import os

from logzero import setup_logger


# Save log file at different place to prevent permission error.
if os.geteuid() == 0:  # root
    LOGGING_FLLEPATH='/tmp/berrynet.log'
else:
    LOGGING_FLLEPATH='{}/.cache/berrynet.log'.format(os.getenv('HOME'))
    # ~/.cache may not exist yet, e.g. on a fresh system or CI runner.
    os.makedirs(os.path.dirname(LOGGING_FLLEPATH), exist_ok=True)

logger = setup_logger(name='berrynet-logger', logfile=LOGGING_FLLEPATH)
