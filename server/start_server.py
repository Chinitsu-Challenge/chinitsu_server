import uvicorn
logging_config = uvicorn.config.LOGGING_CONFIG

logging_config["loggers"]["game_log"] = {
    "handlers": ["default"],
    "level": "INFO",
    "propagate": False,
}
logging_config["handlers"]["game_log"] = {
    "formatter": "default",
    "class": "my_project.ColorStreamHandler",
    "stream": "ext://sys.stderr", 
}

if __name__ == "__main__":
    
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=logging_config)