import pandas as pd
df = pd.read_csv("ml/datasets/llm_prompts_dataset.csv")
print(df["attack_type"].value_counts())
