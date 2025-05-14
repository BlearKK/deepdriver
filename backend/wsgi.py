# wsgi.py
# 在导入任何其他模块之前先导入gevent_monkey模块
import gevent_monkey

# 然后导入应用
from app import app

if __name__ == "__main__":
    app.run()
