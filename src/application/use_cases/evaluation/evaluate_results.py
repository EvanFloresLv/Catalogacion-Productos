import pandas as pd
from dataclasses import dataclass

@dataclass
class EvaluationResultsCommand:
    original: pd.DataFrame
    processed: pd.DataFrame


class EvaluationResultsUseCase:

    def __init__(self, cmd: EvaluationResultsCommand):
        self.command = cmd

    def execute(self):
        # Implement the evaluation logic here
        pass

    def _compare_dataframes(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        # Compare two DataFrames and return the differences
        return df1.compare(df2)
