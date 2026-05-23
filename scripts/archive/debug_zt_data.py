import akshare as ak
import pandas as pd

print("=== 调试：查看涨停板数据结构 ===\n")

# 获取某一天的数据查看结构
test_date = '20260513'
print(f"正在获取 {test_date} 的数据...\n")

try:
    df = ak.stock_zt_pool_em(date=test_date)
    
    print(f"数据形状: {df.shape}")
    print(f"\n所有列名:")
    for i, col in enumerate(df.columns):
        print(f"  {i}: {col}")
    
    print(f"\n前5行数据:")
    print(df.head())
    
    print(f"\n数据类型:")
    print(df.dtypes)
    
    # 查找可能的行业/板块列
    print("\n\n=== 查找行业相关列 ===")
    for col in df.columns:
        if any(keyword in str(col) for keyword in ['行', '板', '概', '概', '类', 'type', 'sector', 'industry']):
            print(f"\n可能匹配: {col}")
            if col in df.columns:
                print(f"唯一值 (前20): {df[col].unique()[:20]}")
    
    # 如果上面没找到，尝试查看所有列的唯一值
    print("\n\n=== 所有列的样本值（帮助识别行业列）===")
    for col in df.columns[:20]:  # 只看前20列
        unique_vals = df[col].unique()[:5]
        print(f"{col}: {unique_vals}")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
