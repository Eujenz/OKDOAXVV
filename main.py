import ok
from src.config import config
from src.preflight import sanitize_result_json

if __name__ == '__main__':
    sanitize_result_json()
    config = config
    ok = ok.OK(config)
    ok.start()
