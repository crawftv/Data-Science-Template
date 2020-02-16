from prefect import task, Flow
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer, MissingIndicator
from sklearn.preprocessing import LabelEncoder, PowerTransformer
import numpy as np

@task
def extract_train_valid_split(input_data, problem, target):
    if problem == "binary classification":
        train_data, valid_data = train_test_split(
            input_data, shuffle=True, stratify=input_data[target],
        )
    elif problem == "regression":
        train_data, valid_data = train_test_split(input_data, shuffle=True,)

    return train_data, valid_data


@task
def extract_nan_features(input_data):
    """a little complicated. map creates a %nan values and returns the feature if greater than the threshold.
        filter simply filters out the false values """
    f = input_data.columns.values
    len_df = len(input_data)
    nan_features = list(
        filter(
            lambda x: x is not False,
            map(
                lambda x: x if input_data[x].isna().sum() / len_df > 0.25 else False, f,
            ),
        )
    )
    return nan_features


@task
def extract_train_data(train_valid_split):
    return train_valid_split[0]


@task
def extract_valid_data(train_valid_split):
    return train_valid_split[1]


@task
def extract_problematic_features(input_data):
    f = input_data.columns.values
    problematic_features = []
    for i in f:
        if "Id" in i:
            problematic_features.append(i)
        elif "ID" in i:
            problematic_features.append(i)
    return problematic_features


@task
def extract_undefined_features(
    input_data, features, target, nan_features, problematic_features
):
    if features == "infer":
        undefined_features = list(input_data.columns)
        undefined_features.remove(target)
    for i in nan_features:
        undefined_features.remove(i)
    for i in problematic_features:
        undefined_features.remove(i)
    return undefined_features


@task
def extract_numeric_features(input_data, undefined_features):
    numeric_features = []
    l = undefined_features
    for i in l:
        if input_data[i].dtype in ["float64", "float", "int", "int64"]:
            if len(input_data[i].value_counts()) / len(input_data) < 0.1:
                pass
            else:
                numeric_features.append(i)
    return numeric_features


@task
def extract_categorical_features(
    input_data, undefined_features, threshold=10,
):
    categorical_features = []
    to_remove = []
    l = undefined_features
    for i in l:
        if len(input_data[i].value_counts()) / len(input_data[i]) < 0.10:
            categorical_features.append(i)
    return categorical_features


@task
def fit_missing_indicator(train_data, undefined_features):
    indicator = MissingIndicator(features="all")
    indicator.fit(train_data[undefined_features])
    return indicator


@task
def transform_missing_indicator_df(data, undefined_features, missing_indicator):
    x = missing_indicator.transform(data[undefined_features])
    x_labels = ["missing_" + i for i in undefined_features]
    missing_indicator_df = pd.DataFrame(x, columns=x_labels)
    columns = [
        i
        for i in list(missing_indicator_df.columns.values)
        if missing_indicator_df[i].max() == True
    ]
    return missing_indicator_df[columns].replace({True: 1, False: 0})


@task
def fit_numeric_imputer(train_data, numeric_features):
    numeric_imputer = SimpleImputer(strategy="median", copy=True)
    numeric_imputer.fit(train_data[numeric_features])
    return numeric_imputer


@task
def impute_numeric_df(numeric_imputer, data, numeric_features):
    x = numeric_imputer.transform(data[numeric_features])
    x_labels = [i + "imputed_" for i in numeric_features]
    imputed_numeric_df = pd.DataFrame(x, columns=x_labels)
    return imputed_numeric_df


@task
def fit_yeo_johnson_transformer(train_imputed_numeric_df):
    yeo_johnson_transformer = PowerTransformer(method="yeo-johnson", copy=True)
    yeo_johnson_transformer.fit(train_imputed_numeric_df)
    return yeo_johnson_transformer


@task
def transform_yeo_johnson_transformer(data, yeo_johnson_transformer):
    yj = yeo_johnson_transformer.transform(data)
    columns = data.columns.values
    columsn = [i + "_yj" for i in columns]
    yj = pd.DataFrame(yj, columns=columns)
    return yj


@task
def fit_target_transformer(problem, target, data):
    if problem == "binary classification":
        return data[target]
    elif problem == "regression":
        target_transformer = PowerTransformer(method="yeo-johnson",copy=True)
        target_transformer.fit(
                np.array(data[target]).reshape(-1,1)
                )
        return target_transformer

@task
def transform_target(problem, target, data,target_transformer):
    if problem == "binary classification":
        return data[target]
    elif problem == "regression":
        target_array = target_transformer.transform(
            np.array(data[target]).reshape(-1, 1)
        )
        target_array = pd.DataFrame(target_array, columns=[target])
        return target_array


@task
def fit_target_encoder(train_imputed_categorical_df, train_transformed_target):
    te = TargetEncoder(cols=train_imputed_categorical_df.columns.values)
    te.fit(X=self.train_imputed_categorical_df, y=self.train_transformed_target)
    return te


@task
def merge_transformed_data(encoded_df, yeo_johnson_df, missing_df):
    transformed_data = (
        encoded_df.merge(yeo_johnson_df, left_index=True, right_index=True)
        .merge(missing_df, left_index=True, right_index=True)
        .replace(np.nan, 0)
    )
    return transformed_data


@task
def fit_hbos_transformer(train_transformed_data):
    hbos = HBOS()
    hbos.fit(train_transformed_data)
    return hbos_transformer


@task
def transfom_hbos_transformer(data, hbos_transformer):
    hbos_transformed = hbos_transformer.predict(data)
    return hbos_t


# with Flow("data_cleaning") as flow:
#    train_data, valid_data = extract_input_meta_data(input_data, problem)
#    nan_features = nan_features(input_data)
#    problematic_features = problematic_features(input_data)
#    undefined_features = undefined_features(input_data)
#    numeric_features = numeric_features(input_data)
#    categorical_features = categorical_features(input_data)


# if __name__ == "__main__":
#    flow.run()
