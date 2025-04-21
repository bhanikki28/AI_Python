import streamlit as st
import pandas as pd 
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon=" 💰", layout = "wide")


def main():
    st.title("Simple Finance Dashboard")