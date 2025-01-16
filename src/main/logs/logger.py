import logging


def setup_logger(name: str):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        handlers=[
            # uncomment the following line to log to a file
            # logging.FileHandler("project.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

