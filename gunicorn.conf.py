import multiprocessing

bind = "0.0.0.0:{}".format(__import__("os").environ.get("PORT", "8000"))
workers = 2
threads = 4
timeout = 120
graceful_timeout = 30
keepalive = 5
