import asyncio
import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


async def task_one():
    logger.info("Task One started.")
    for i in range(20, -1, -1):
        logger.info(f"Countdown: {i} minutes")
        await asyncio.sleep(60)  # Sleep for 1 minute
    logger.info("Task One completed.")

async def task_two():
    logger.info("Task Two started.")
    for i in range(20, -1, -1):
        logger.info(f"Countdown: {i} minutes")
        await asyncio.sleep(60)  # Sleep for 1 minute
    logger.info("Task Two completed.")

async def main():
    logger.info("Starting...")
    await asyncio.sleep(1800)  # Sleep until 9:30 AM

    logger.info("Launching Task One...")
    task_one_task = asyncio.create_task(task_one())

    logger.info("Waiting until 3:00 PM to continue...")
    await asyncio.sleep(10260)  # Sleep until 3:00 PM

    logger.info("Launching Task Two...")
    task_two_task = asyncio.create_task(task_two())

    logger.info("Waiting until 4:00 PM...")
    await asyncio.sleep(3600)  # Sleep until 4:00 PM

    await task_one_task
    await task_two_task

    logger.info("Program done.")

if __name__ == "__main__":
    asyncio.run(main())

