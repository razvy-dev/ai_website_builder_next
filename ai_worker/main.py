import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from ai_worker.factory import Factory
from ai_worker.component_worker import (
    ComponentState, 
    design_sanity_schema, 
    save_sanity_schema,
    design_query,
    save_query,
    design_component,
    save_component,
    populate_component_data
)
from ai_worker.utils.prompts import generate_sanity_schema, generate_query, generate_nextjs_component
from sqlmodel import Session, select
from db.migration import SectionComponent
from db.manager import get_project_session
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
        print(f"[{component_name}] 📋 Generating Sanity schema...")
        state = design_sanity_schema(
            initial_state, 
            generate_sanity_schema, 
            ai_client.design_sanity_schema_model
        )
        
        # 3. Save sanity schema
        print(f"[{component_name}] 💾 Saving schema...")
        state = save_sanity_schema(state)
        
        # 4. Design query
        print(f"[{component_name}] 🔍 Generating GROQ query...")
        state = design_query(
            state,
            generate_query,
            ai_client.design_query_model
        )
        
        # 5. Save query
        print(f"[{component_name}] 💾 Saving query...")
        state = save_query(state)
        
        # 6. Design component
        print(f"[{component_name}] ⚛️  Generating Next.js component...")
        state = design_component(
            state,
            generate_nextjs_component,
            ai_client.design_component_model
        )
        
        # 7. Save component (also registers in BlockRenderer.tsx)
        print(f"[{component_name}] 💾 Saving component & registering...")
        state = save_component(state)
        
        # 8. Populate Sanity CMS with data
        print(f"[{component_name}] 📊 Populating CMS data...")
        final_state = populate_component_data(state)
        
        print(f"[{component_name}] ✅ Complete! Component: {final_state.get('component_name', 'unknown')}.tsx")

        return {
            "component_data": component_data,
            "status": "success",
            "error": None,
            "schema_filename": final_state.get("sanity_schema_filename", ""),
            "component_name": final_state.get("component_name", "")
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

def get_all_section_components(project_id: str) -> list[dict]:
    """
    Retrieve all section components from the database.
    
    Args:
        project_id: The project identifier
        
    Returns:
        List of dictionaries containing all section component data
    """
    session = get_project_session(project_id)
    
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
        
        # Get project path from global state
        from ai_worker.utils.global_state import get_state
        state = get_state()
        project_path = state.project_path
        
        if not project_path:
            # Fallback to hardcoded path if not configured
            PYTHON_PROJECT_ROOT = Path(__file__).resolve().parent.parent
            BUILDER_ROOT = PYTHON_PROJECT_ROOT.parent
            OUTPUT_DIR = BUILDER_ROOT / "test_project_init"
            project_path = str(OUTPUT_DIR)
            print(f"⚠️  No project path in global state, using fallback: {project_path}")
        else:
            print(f"✓ Using project path from global state: {project_path}")
        
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
                    component_info = f" → {result.get('component_name', 'N/A')}.tsx" if result["status"] == "success" else ""
                    print(f"[{completed}/{len(components)}] {status_symbol} {component['name']}{component_info}")
                    
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
            print(f"\n📁 Output locations:")
            print(f"   • Schemas: {project_path}/studio/src/schemaTypes/objects/")
            print(f"   • Components: {project_path}/frontend/app/components/")
            print(f"   • Queries: {project_path}/frontend/sanity/lib/queries.ts")
            print(f"   • BlockRenderer: {project_path}/frontend/app/components/BlockRenderer.tsx")
        
        return ai_client
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()