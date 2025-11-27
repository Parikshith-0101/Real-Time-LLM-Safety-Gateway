import pandas as pd
df = pd.read_csv("dataset/malicious_llm_prompts_train.csv")
print(df["attack_type"].value_counts())
