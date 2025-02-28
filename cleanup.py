# cleanup.py

import os
import threading
from my_logger import logging, logger_thd

def cleanup_wav(wav_path):
    logging.info(f"Called method: cleanup_wav() curThd={threading.current_thread().name}  Cleaning path={wav_path}")
    """
    Deletes the specified WAV file.
    
    Args:
        wav_path (str): Path to the WAV file to delete.
    """
    try:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
            ## os.remove(wav_path)
            logging.info(f"Cleaned up temporary WAV file: {wav_path}")
        else:
            logging.warning(f"WAV file does not exist: {wav_path}")
    except Exception as e:
        logging.error(f"Failed to delete WAV file {wav_path}: {e}")
    logging.info(f"Finishing method: cleanup_wav() curThd={threading.current_thread().name}")

