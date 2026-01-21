import streamlit as st
from st_supabase_connection import SupabaseConnection

def get_supabase_client():
    """
    Returns the Supabase client from the Streamlit connection.
    """
    return st.connection("supabase", type=SupabaseConnection).client

def login(email, password):
    """
    Authenticates the user with Supabase using email and password.
    Stores various tokens and user info in st.session_state on success.
    Returns:
        tuple: (success (bool), message (str))
    """
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.user and response.session:
            # Store essential session data
            st.session_state.access_token = response.session.access_token
            st.session_state.refresh_token = response.session.refresh_token
            st.session_state.user_info = {
                "id": response.user.id,
                "email": response.user.email,
                "role": response.user.role
            }
            
            # Legacy fields for backward compatibility, if needed by other pages
            st.session_state.logged_in = True
            st.session_state.username = response.user.email
            st.session_state.user_id = response.user.id
            
            return True, "Login successful"
        else:
            return False, "Login failed: No user or session returned"
    except AuthApiError as e:
        return False, f"Login failed: {e.message}"
    except Exception as e:
        return False, f"Login failed: {str(e)}"

def sign_up(email, password):
    """
    Signs up a new user.
    """
    client = get_supabase_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
             return True, "Account created! You can now sign in."
        else:
             return False, "Sign up failed."
    except Exception as e:
        return False, f"Error: {str(e)}"

def logout():
    """
    Logs out the user by clearing session state and calling sign_out on the client (good practice).
    """
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except:
        pass  # Ignore if already signed out on server side

    # Clear our session state
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_id = None
    
    # Optional: Rerun to refresh UI state immediately
    # st.rerun() 

def get_authenticated_user():
    """
    Verifies if there is a valid session locally checks. 
    Does NOT perform a network call to verify token on every check to save latency,
    assuming 'access_token' presence implies logged in for UI purposes.
    
    For strict security on critical actions, you should use the client 
    to get the user passing the access token.
    """
    if st.session_state.get("logged_in") and st.session_state.get("access_token"):
        return st.session_state.user_info
    return None

def verify_token_server_side():
    """
    Explicitly checks with Supabase if the current access_token is valid.
    Useful for sensitive pages.
    """
    token = st.session_state.get("access_token")
    if not token:
        return None
    
    client = get_supabase_client()
    try:
        user = client.auth.get_user(token)
        return user
    except:
        return None
