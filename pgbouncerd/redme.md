# pgbouncerd
## 1.功能
* 1. 启动、停止、重启pgbouncer
* 2. 监控检查pgbouncer进程
* 3. 在pgbouncer进程挂掉时自动恢复pgbouncer
* 4. 在已经启动pgbouncer的环境下，自动接管pgbouncer进行监控、自动恢复
## 2. 依赖
* `psutil` >= 0.4.1
* `setproctitle` >= 1.1.10
## 3. 安装
```
sudo python setup.py install
```
## 4. 使用
```
su - postgres
pgbouncerd  start -P /usr/local/pgbouncer/conf/server.ini
```
### 5. 帮助
```
Usage: pgbouncerd [start|stop|restart] [-U <username>] [-P <conf_path>]

Options:
  -h, --help            show this help message and exit
  -U USERNAME, --username=USERNAME
                        PgBouncer user name (default: "postgres").
  -P config_path, --path=config_path
                        The abspath path of PgBouncer configure file
```
