import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from ai_worker.factory import Factory
from sqlmodel import Session, select
from db.migration import SectionComponent, create_db_and_tables
from playwright_tester import Playwright

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

def process_single_component(component_data: dict, ai_client, playwright) -> dict:
    """
    Process a single component through the AI workflow.
    This function will be called in parallel for each component.
    
    Args:
        component_data: Dictionary containing component data from database
        ai_client: Initialized AI client (OpenAI, Claude, or Gemini)
        playwright: Playwright instance for testing
        
    Returns:
        Dictionary with component_data and processing results
    """
    try:
        component_name = component_data["name"]
        print(f"[{component_name}] Starting processing...")
        
        # TODO: Integrate with component_worker here
        # Example workflow:
        # 1. Create ComponentState from component_data
        # initial_state = ComponentState(
        #     node_id=component_data["node_id"],
        #     component_name=component_data["name"],
        #     raw_node_json=component_data["raw_node_json"],
        #     width=component_data["width"],
        #     height=component_data["height"],
        #     figma_screenshot=component_data["screenshot"],
        #     component_code="",
        #     query_code="",
        #     typescript_type_code="",
        #     sanity_schema_code="",
        #     done=False
        # )
        # 
        # 2. Run through AI workflow (component_worker.app)
        # result = app.invoke(initial_state)
        # 
        # 3. Test with playwright
        # test_result = playwright.test_component(result["component_code"])
        # 
        # 4. Return results
        
        print(f"[{component_name}] Processing complete")
        return {
            "component_data": component_data,
            "status": "success",
            "error": None
        }
        
    except Exception as e:
        print(f"[{component_data['name']}] Error: {e}")
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

        components = get_all_components()

        print("AI client is ready for use!")
        print(f"Provider: {ai_client.provider}")
        print(f"Model: {ai_client.model}")
        
        # Initialize Playwright for testing
        playwright = Playwright()
        
        # Process components in parallel
        max_workers = 5  # Adjust based on API rate limits and system resources
        results = []
        
        print(f"\n=== Processing {len(components)} components in parallel (max {max_workers} workers) ===")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all component processing tasks
            future_to_component = {
                executor.submit(process_single_component, comp, ai_client, playwright): comp
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
                    print(f"[{completed}/{len(components)}] {status_symbol} {component['name']}")
                    
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
        
        return ai_client
        
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    main()