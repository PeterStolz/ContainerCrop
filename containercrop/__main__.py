import logging

from containercrop.retention import RetentionArgs, main

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(retention_args=RetentionArgs.from_env()))
