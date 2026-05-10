import streamlit_google_auth
import google_auth_oauthlib
import oauthlib
import streamlit
print(f"streamlit_google_auth: {streamlit_google_auth.__version__ if hasattr(streamlit_google_auth, '__version__') else 'N/A'}")
print(f"google_auth_oauthlib: {google_auth_oauthlib.__version__}")
print(f"oauthlib: {oauthlib.__version__}")
print(f"streamlit: {streamlit.__version__}")
