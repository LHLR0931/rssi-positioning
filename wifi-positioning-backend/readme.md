# WiFi RSSI 室内定位后端

## 环境配置（首次运行）

```powershell
# 1. 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库（生成 db_new.sqlite3）
python manage.py migrate

# 4. 启动后端服务
python manage.py runserver 0.0.0.0:8000
```

> 如遇缺包报错，补装以下依赖：
> ```powershell
> pip install lightning -i https://pypi.org/simple
> pip install torch torch-geometric
> pip install --upgrade threadpoolctl tensorboard tensorboardX
> ```

---

## 两个数据库说明

| 文件 | 用途 |
|------|------|
| `db_new.sqlite3` | Django 默认库，所有实验数据、训练、预测都走这里 |
| `db.sqlite3` | 历史参考数据，供新人验证后端接口是否正常，与 Django 无关 |

---

## 完整实验流程

### 第零步：清空实验数据库

**每次开始新实验前必须执行**，防止旧数据污染结果。

```powershell
# 在 wifi-positioning-backend/ 目录下运行
.\reset_wifidata.ps1
```

脚本会自动：
- 将当前 WiFiData 导出备份到 `backup/dump_WiFiData_<时间戳>.json`
- 备份数据库文件到 `backup/db_new_<时间戳>.sqlite3`
- 清空 WiFiData 表（保留用户账号和 Token 不动）
- 打印各 data_type 计数，确认清空成功（应全为 0）

---

### 第一步：采集训练数据（手机端）

在每个采集点**多次扫描**（建议每个点至少扫描 5 次），通过手机 App 或 Postman 发送：

```
POST http://<服务器IP>:8000/api/wifidata/
Content-Type: application/json

{
  "x": 2.0,
  "y": 3.5,
  "wifiData": [
    {"ssid": "MyWifi",    "bssid": "aa:bb:cc:dd:ee:ff", "rssi": -65},
    {"ssid": "OtherWifi", "bssid": "11:22:33:44:55:66", "rssi": -72}
  ]
}
```

字段说明：
- `x` / `y`：该采集点的真实坐标（单位：米）
- `wifiData`：手机扫描到的所有 WiFi 信号列表
- `data_type` 不用手动填，下一步会自动划分

---

### 第二步：划分训练 / 验证 / 测试集

所有点采集完后，执行一次自动划分（比例 6:2:2）：

```
POST http://<服务器IP>:8000/api/wifidata/splitdata/
Content-Type: application/json

{}
```

返回示例：
```json
{
  "total": 200,
  "train": 120,
  "val": 40,
  "test": 40,
  "ratio": "60% / 20% / 20%"
}
```

---

### 第三步：训练模型

**CNN 模型：**

```powershell
.\train.ps1

# 可选参数（以下为默认值）：
.\train.ps1 -MaxEpochs 500 -LearningRate 2e-4 -BatchSize 2 -NumWorkers 1
```

训练完成后 checkpoint 自动保存到 `cnn_checkpoints/last.ckpt`。

**GNN 模型：**

```powershell
.\train_gnn.ps1

# 可选参数（以下为默认值）：
.\train_gnn.ps1 -MaxEpochs 200 -LearningRate 2e-3 -BatchSize 4 -ModeType TAGConv
```

训练完成后 checkpoint 自动保存到 `gnn_cnn_checkpoints/last.ckpt`。

训练过程可视化：

```powershell
tensorboard --logdir=logs
# 浏览器访问 http://localhost:6006
```

> **注意**：如果采集了新数据导致 WiFi AP（BSSID）的种类发生变化，必须重新训练模型，不能沿用旧 checkpoint。

---

### 第四步：预测测试

启动后端服务后，手机 App 或 Postman 发送当前扫描数据：

**CNN 预测：**

```
POST http://<服务器IP>:8000/api/wifidata/cnnpredict/
Content-Type: application/json

{
  "wifiData": [
    {"ssid": "MyWifi",    "bssid": "aa:bb:cc:dd:ee:ff", "rssi": -68},
    {"ssid": "OtherWifi", "bssid": "11:22:33:44:55:66", "rssi": -75}
  ],
  "x": 2.0,
  "y": 3.5
}
```

**GNN 预测：**

```
POST http://<服务器IP>:8000/api/wifidata/gnnpredict/
Content-Type: application/json

{
  "wifiData": [
    {"ssid": "MyWifi",    "bssid": "aa:bb:cc:dd:ee:ff", "rssi": -68},
    {"ssid": "OtherWifi", "bssid": "11:22:33:44:55:66", "rssi": -75}
  ],
  "x": 2.0,
  "y": 3.5
}
```

> `x` / `y` 为可选字段，填入真实坐标后返回值会包含预测误差。

返回示例：
```json
{
  "x": 2.13,
  "y": 3.41,
  "error_meters": 0.21
}
```

---

### 流程总览

```
.\reset_wifidata.ps1
        |  清空 db_new.sqlite3
        v
手机多点采集  -->  POST /api/wifidata/   （每个点多次扫描）
        |
        v
POST /api/wifidata/splitdata/            （6:2:2 自动划分）
        |
        v
.\train.ps1  或  .\train_gnn.ps1         （训练，生成 checkpoint）
        |
        v
POST /api/wifidata/cnnpredict/
  或   /api/wifidata/gnnpredict/          （预测 + 误差）
```

---

## 所有 API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/wifidata/` | 查询所有 WiFiData |
| POST | `/api/wifidata/` | 上传采集数据 |
| DELETE | `/api/wifidata/bycoor/` | 按坐标删除数据 |
| GET/PUT/DELETE | `/api/wifidata/<id>/` | 单条数据操作 |
| POST | `/api/wifidata/splitdata/` | 6:2:2 划分数据集 |
| GET | `/api/wifidata/export/` | 导出数据为 JSON |
| POST | `/api/wifidata/import/` | 从 JSON 导入数据 |
| GET | `/api/wifidata/survey_xy/` | 查询所有采集点坐标 |
| POST | `/api/wifidata/predict/` | KNN / RF 在线训练预测 |
| POST | `/api/wifidata/fingerprinting/` | 指纹法 KNN / RF 预测 |
| POST | `/api/wifidata/cnnpredict/` | CNN 模型预测 |
| POST | `/api/wifidata/gnnpredict/` | GNN 模型预测 |
| POST | `/api/signup/` | 注册账号 |
| POST | `/api/login/` | 登录 |
