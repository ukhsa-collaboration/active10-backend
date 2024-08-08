import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    nhs_login_authority_url: str
    nhs_login_client_id: str
    nhs_login_callback_url: str
    nhs_login_scopes: str
    nhs_api_url: str
    nhs_api_key: str
    secret: str
    db_host: str
    db_port: str
    db_user: str
    db_pass: str
    db_name: str
    app_uri: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Config()


logger = logging.getLogger('Application-Logs')
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
