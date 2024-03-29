from containercrop.retention import main, RetentionArgs
import logging
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(retention_args=RetentionArgs.from_env()))