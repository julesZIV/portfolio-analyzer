import streamlit as st

def afficher_profil():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### My profile")
    st.sidebar.write("**Name**: Jules Zivkovic")
    st.sidebar.write("**Email**: jules.zivkovic@gmail.com")
    st.sidebar.write("**Opportunities**: \n - searching for a four months internship (August-November 2027) \n" 
    "- six months internship (april-october 2027)")
    st.sidebar.write("**Teacher**: Mano Mathew")
