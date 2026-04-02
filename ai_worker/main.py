import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from ai_worker.factory import Factory
from ai_worker.component_worker import ComponentState, design_sanity_schema, save_sanity_schema
from ai_worker.utils.prompts import generate_sanity_schema
from sqlmodel import Session, select
from db.migration import SectionComponent, create_db_and_tables
from ai_worker.playwright_tester import Playwright
from pathlib import Path

def get_ai_client():
    """
    Prompts the user to select an AI provider and returns a ready-to-use AI client.
    
    Returns:
        Factory: An initialized AI client instance (OpenAI, Claude, or Gemini)
    """
    print("\n=== AI Provider Selection ===")
    print("Available providers:")
    print("1. OpenAI (GPT-4, GPT-3.5, etc.)")
    print("2. Claude (Claude 3 Opus, Sonnet, Haiku)")
    print("3. Gemini (Gemini Pro, etc.)")
    
    # Get provider choice
    while True:
        choice = input("\nSelect provider (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    provider_map = {
        '1': ('openai', 'gpt-4', 'OPENAI_API_KEY'),
        '2': ('claude', 'claude-3-5-sonnet-20241022', 'ANTHROPIC_API_KEY'),
        '3': ('gemini', 'gemini-pro', 'GOOGLE_API_KEY')
    }
    
    provider_name, default_model, env_key = provider_map[choice]
    
    # Get model name
    model = input(f"Enter model name (default: {default_model}): ").strip()
    if not model:
        model = default_model
    
    # Get API key
    api_key = os.getenv(env_key)
    if not api_key:
        api_key = input(f"Enter your {provider_name.upper()} API key: ").strip()
        if not api_key:
            raise ValueError("API key is required")
    else:
        print(f"Using API key from environment variable: {env_key}")
    
    # Create and return AI client
    print(f"\nInitializing {provider_name.upper()} with model: {model}")
    ai_client = Factory.create(provider_name, model, api_key)
    print("✓ AI client ready!\n")
    
    return ai_client

def process_single_component(component_data: dict, ai_client, project_path: str) -> dict:
    """
    Process a single component through the AI workflow.
    This function will be called in parallel for each component.
    
    Args:
        component_data: Dictionary containing component data from database
        ai_client: Initialized AI client (OpenAI, Claude, or Gemini)
        project_path: Path to the generated Next.js project
        
    Returns:
        Dictionary with component_data and processing results
    """
    try:
        component_name = component_data["name"]
        print(f"[{component_name}] Starting sanity schema generation...")
        
        # 1. Create ComponentState from component_data
        initial_state: ComponentState = {
            "key": component_data.get("node_id", ""),
            "node_id": component_data["node_id"],
            "component_name": component_data["name"],
            "component_description": "",
            "raw_node_json": component_data["raw_node_json"],
            "width": component_data["width"],
            "height": component_data["height"],
            "component_set_key": "",
            "figma_screenshot": component_data["screenshot"],
            "component_code": "",
            "query_code": "",
            "typescript_type_code": "",
            "sanity_schema_code": "",
            "sanity_schema_filename": "",
            "project_path": project_path,
            "done": False
        }
        
        # 2. Design sanity schema
        print(f"[{component_name}] Calling AI to generate schema...")
        state_after_design = design_sanity_schema(
            initial_state, 
            generate_sanity_schema, 
            ai_client.design_sanity_schema_model
        )
        
        # 3. Save sanity schema
        print(f"[{component_name}] Saving schema to project...")
        final_state = save_sanity_schema(state_after_design)
        
        print(f"[{component_name}] ✓ Complete - Schema: {final_state.get('sanity_schema_filename', 'unknown')}.ts")
        return {
            "component_data": component_data,
            "status": "success",
            "error": None,
            "schema_filename": final_state.get("sanity_schema_filename", "")
        }
        
    except Exception as e:
        print(f"[{component_data['name']}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "component_data": component_data,
            "status": "error",
            "error": str(e)
        }

def get_all_components(db_path: str = "figma.db") -> list[dict]:
    """
    Retrieve all section components from the database.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        List of dictionaries containing all section component data
    """
    session = create_db_and_tables(db_path)
    
    try:
        # Query all section components, ordered by page, frame, and order
        statement = select(SectionComponent).order_by(
            SectionComponent.page_id,
            SectionComponent.root_frame_id,
            SectionComponent.depth,
            SectionComponent.order
        )
        components = session.exec(statement).all()
        
        # Convert to list of dicts with all data
        components_data = []
        for component in components:
            components_data.append({
                "node_id": component.node_id,
                "page_id": component.page_id,
                "root_frame_id": component.root_frame_id,
                "parent_node_id": component.parent_node_id,
                "depth": component.depth,
                "order": component.order,
                "name": component.name,
                "width": component.width,
                "height": component.height,
                "raw_node_json": component.raw_node_json,
                "screenshot": component.screenshot,
            })
        
        print(f"Retrieved {len(components_data)} section components from database")
        return components_data
        
    finally:
        session.close()


def main():
    """Main entry point for the AI website builder"""
    try:
        # Get AI client from user
        ai_client = get_ai_client()

        all_components = get_all_components()
        
        # Limit to first 5 components for testing
        components = all_components[:5]
        print(f"\n⚠️  Testing mode: Processing only first {len(components)} of {len(all_components)} components")

        print("AI client is ready for use!")
        print(f"Provider: {ai_client.provider}")
        print(f"Model: {ai_client.model}")
        
        # Get project path
        PYTHON_PROJECT_ROOT = Path(__file__).resolve().parent.parent
        BUILDER_ROOT = PYTHON_PROJECT_ROOT.parent
        OUTPUT_DIR = BUILDER_ROOT / "test_project_init" # TODO: do not hardcode this. find a way to manage global state for this project
        project_path = OUTPUT_DIR
        print(f"Using project path: {project_path}")
        
        # Process components in parallel
        max_workers = 3  # Reduced for testing
        results = []
        
        print(f"\n=== Processing {len(components)} components in parallel (max {max_workers} workers) ===")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all component processing tasks
            future_to_component = {
                executor.submit(process_single_component, comp, ai_client, project_path): comp
                for comp in components
            }
            
            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_component):
                component = future_to_component[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    status_symbol = "✓" if result["status"] == "success" else "✗"
                    schema_info = f" ({result.get('schema_filename', 'N/A')}.ts)" if result["status"] == "success" else ""
                    print(f"[{completed}/{len(components)}] {status_symbol} {component['name']}{schema_info}")
                    
                except Exception as exc:
                    print(f"[{completed}/{len(components)}] ✗ {component['name']} generated exception: {exc}")
                    results.append({
                        "component_data": component,
                        "status": "error",
                        "error": str(exc)
                    })
        
        # Print summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        print(f"\n=== Processing Complete ===")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        
        if successful > 0:
            print(f"\n📁 Schemas saved to: {project_path}/studio/src/schemaTypes/objects/")
            print(f"📝 Index updated at: {project_path}/studio/src/schemaTypes/index.ts")
        
        return ai_client
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()