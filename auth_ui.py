import streamlit as st
from db_utils import init_user_table, add_user, verify_user, is_admin_user
from audit_utils import init_audit_table, add_audit_log


def show_auth():
    # 初始化表
    init_user_table()
    init_audit_table()

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.is_admin = False

    st.sidebar.title("账号管理")
    options = ['登录', '注册']
    if st.session_state.logged_in:
        options.append('注销')
    menu = st.sidebar.selectbox('请选择操作', options)

    if menu == '登录':
        st.sidebar.subheader('用户登录')
        user = st.sidebar.text_input('用户名', key='login_user')
        pw = st.sidebar.text_input('密码', type='password', key='login_pw')
        if st.sidebar.button('登录'):
            if verify_user(user, pw):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.is_admin = is_admin_user(user)
                st.sidebar.success(f'登录成功，欢迎 {user}!')
                add_audit_log(user, 'login')
            else:
                st.sidebar.error('用户名或密码错误。')

    elif menu == '注册':
        st.sidebar.subheader('新用户注册')
        new_user = st.sidebar.text_input('用户名', key='reg_user')
        new_pw = st.sidebar.text_input('密码', type='password', key='reg_pw')
        new_pw_conf = st.sidebar.text_input('确认密码', type='password', key='reg_pw_conf')
        if st.sidebar.button('注册'):
            if not new_user or not new_pw:
                st.sidebar.error('用户名和密码不能为空。')
            elif new_pw != new_pw_conf:
                st.sidebar.error('两次密码不一致。')
            else:
                success = add_user(new_user, new_pw)
                if success:
                    st.sidebar.success('注册成功，请登录。')
                    add_audit_log(new_user, 'register')
                else:
                    st.sidebar.error('用户名已存在。')

    elif menu == '注销':
        user = st.session_state.username
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.is_admin = False
        st.sidebar.info('已注销。')
        add_audit_log(user, 'logout')

    return st.session_state.logged_in, st.session_state.username, st.session_state.is_admin