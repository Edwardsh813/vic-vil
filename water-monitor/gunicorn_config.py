# Gunicorn configuration for Water Monitor
bind = "127.0.0.1:5000"
workers = 2
threads = 4
timeout = 120
accesslog = "/home/hunter/projects/vic-vil/water-monitor/access.log"
errorlog = "/home/hunter/projects/vic-vil/water-monitor/error.log"
capture_output = True
