from core.main import MultiAgentSystem
import asyncio

async def test_simple_query():
    # Setup logging
    Logger.setup(log_level="INFO")
    logger = Logger.get_logger()
    
    # Initialize system
    system = MultiAgentSystem(max_iterations=10)
    
    # Test query
    query = "Write me a bash script that prints hello world."
    
    logger.info("Starting task processing...")
    logger.info(f"Query: {query}")
    
    try:
        result = await system.process_query(query)
        logger.info("\nTask completed!")
        logger.info("Generated solution:")
        logger.info(f"\n{result}")
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_simple_query()) 