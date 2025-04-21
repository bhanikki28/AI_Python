import streamlit as st
import pandas as pd 
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon=" 💰", layout = "wide")


def load_transactions(transaction_file):
    print(f"Reading the transaction file : {transaction_file.name}")
    try:
        df = pd.read_csv(transaction_file)
        #df.columns = [ col.strip for col in df.columns]
        df["Amount"] = df["Amount"].str.replace(",","").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        st.write(df)
        return df
    except Exception as e:
        st.error(f"Error processing the file : {str(e)}")
        return None


def main():
    st.title("Simple Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your transaction csv file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

main()   
