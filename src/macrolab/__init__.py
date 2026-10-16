"""macro-lab 公共代码：数据源取数、指标 ID 表、运行记录。"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXPERIMENTS = REPO / "experiments"
DATA_IDS = REPO / "docs" / "data-ids"
