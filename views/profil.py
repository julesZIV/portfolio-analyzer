import streamlit as st

def afficher_profil():
    st.sidebar.markdown("---") 
    st.sidebar.markdown("### Mon Profil")
    st.sidebar.write("**Nom**: Jules Zivkovic")
    st.sidebar.write("**Email**: jules.zikovic@gmail.com")
    st.sidebar.write("**Opportunities**: \n - searching for a four months internship (Aout-novembre 2027) \n" 
    "- six mouths internship (april-october 2027)")
    st.sidebar.write("**Teacher**: Mano Mathew")
