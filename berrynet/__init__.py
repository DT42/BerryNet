import os

from logzero import setup_logger


# Save log file at different place to prevent permission error.
if os.geteuid() == 0:  # root
    LOGGING_FLLEPATH='/tmp/berrynet.log'
else:
    LOGGING_FLLEPATH='{}/.cache/berrynet.log'.format(os.getenv('HOME'))

logger = setup_logger(name='berrynet-logger', logfile=LOGGING_FLLEPATH)
