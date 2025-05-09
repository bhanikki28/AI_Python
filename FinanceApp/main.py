import streamlit as st
import pandas as pd 
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon=" 💰", layout = "wide")


category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized" : []
    }


if os.path.exists(category_file):
    with open("categories.json","r") as f:
        st.session_state.categories = json.load(f)


def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)



def load_transactions(transaction_file):
    print(f"Reading the transaction file : {transaction_file.name}")
    try:
        df = pd.read_csv(transaction_file)
        #df.columns = [ col.strip for col in df.columns]
        df["Amount"] = df["Amount"].str.replace(",","").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        return df
    except Exception as e:
        st.error(f"Error processing the file : {str(e)}")
        return None


def main():
    st.title("Simple Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your transaction csv file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()
            tab1, tab2 = st.tabs( ["Expenses(Debits)", "Payments(Credits)"])
            with tab1:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.success(f"Added New Category : {new_category}")
                        st.rerun()

                st.write(debits_df)
            with tab2:
                st.write(credits_df)

main()   
