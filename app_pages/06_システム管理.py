import datetime as dt

import streamlit as st
from sqlalchemy import select

from app.auth import hash_password, logout_button, require_login
from app.db import get_session, init_db
from app.models import ROLE_MANAGER, ROLES, BranchMaster, ErrorLog, HeadquartersMaster, RegionMaster, User
from app.seal import seal_img_tag
from app.ui import apply_theme

init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("システム管理")
st.caption("ユーザーの権限・組織属性の割り当てまでを行います。社判登録・承認申請の処理自体はマネージャーが行います。")

if not user.can_manage_users:
    st.error("この画面はシステム管理者のみ利用できます。")
    st.stop()

tab_users, tab_org, tab_logs = st.tabs(["ユーザー管理", "組織属性マスタ", "エラーログ"])

# ---------------------------------------------------------------
# ユーザー管理
# ---------------------------------------------------------------
with tab_users:
    headquarters = session.execute(select(HeadquartersMaster)).scalars().all()
    branches = session.execute(select(BranchMaster)).scalars().all()
    regions = session.execute(select(RegionMaster)).scalars().all()
    # 統合済み(active=False)の統括部門・拠点は、新規登録の選択肢からは除外する。
    # ただし既にその統括部門・拠点が割り当てられているユーザーの表示が壊れないよう、
    # 一覧表示用のラベルには統合済みの名称もそのまま残しておく。
    hq_options = {h.id: h.name for h in headquarters if h.active}
    branch_options = {b.id: b.name for b in branches if b.active}
    region_options = {r.id: r.name for r in regions}
    hq_labels_all = {h.id: (h.name if h.active else f"{h.name}(統合済み)") for h in headquarters}
    branch_labels_all = {b.id: (b.name if b.active else f"{b.name}(統合済み)") for b in branches}

    st.subheader("新規ユーザー登録")
    with st.form("new_user_form", clear_on_submit=True):
        username = st.text_input("ユーザーID")
        display_name = st.text_input("表示名")
        password = st.text_input("初期パスワード", type="password")
        role = st.selectbox("ロール", options=ROLES)
        hq_id = st.selectbox("統括部門", options=[None] + list(hq_options.keys()), format_func=lambda i: "未設定" if i is None else hq_options[i])
        branch_id = st.selectbox("拠点(部門名称)", options=[None] + list(branch_options.keys()), format_func=lambda i: "未設定" if i is None else branch_options[i])
        region_id = st.selectbox("地域区分", options=[None] + list(region_options.keys()), format_func=lambda i: "未設定" if i is None else region_options[i])
        if st.form_submit_button("登録", type="primary"):
            existing_usernames = {u.username for u in session.execute(select(User)).scalars().all()}
            existing_display_names = {u.display_name for u in session.execute(select(User)).scalars().all() if u.display_name}
            if not username or not password:
                st.error("ユーザーIDと初期パスワードは必須です。")
            elif username in existing_usernames:
                st.error(f"ユーザーID「{username}」は既に使われています。")
            elif display_name and display_name in existing_display_names:
                st.error(f"表示名「{display_name}」は既に使われています。別の表示名にしてください。")
            else:
                session.add(
                    User(
                        username=username,
                        display_name=display_name,
                        password_hash=hash_password(password),
                        role=role,
                        headquarters_id=hq_id,
                        branch_id=branch_id,
                        region_id=region_id,
                    )
                )
                session.commit()
                st.success("登録しました。")
                st.rerun()

    st.divider()
    st.subheader("ユーザー一覧")
    search = st.text_input("検索(ユーザーIDまたは表示名)", key="user_search")

    users = session.execute(select(User)).scalars().all()
    if search:
        users = [u for u in users if search.lower() in u.username.lower() or search.lower() in (u.display_name or "").lower()]

    managers_by_branch: dict[int | None, list[User]] = {}
    for u in session.execute(select(User)).scalars().all():
        if u.role == ROLE_MANAGER and u.active:
            managers_by_branch.setdefault(u.branch_id, []).append(u)

    for u in users:
        with st.container(border=u.active):
            if not u.active:
                st.markdown(":gray[⚫ 無効化されたアカウント]")
            c0, c1, c2, c3, c4, c5 = st.columns([1.4, 2, 2, 2, 2, 2])
            with c0:
                if u.seal_svg:
                    st.markdown(seal_img_tag(u.seal_svg, size=48), unsafe_allow_html=True)
                    st.markdown(':green[**印鑑: 登録済み**]')
                else:
                    st.markdown(':gray[印鑑: 未登録]')
            c1.markdown(f"**{u.username}**")
            c1.caption(u.display_name)
            new_role = c2.selectbox("ロール", options=ROLES, index=ROLES.index(u.role), key=f"role_{u.id}", disabled=not u.active)
            # 選択肢は基本的に有効な統括部門・拠点のみだが、既に統合済みのものが
            # 割り当てられているユーザーについては、そのままその名称も選択肢に含めて
            # 表示が崩れない(indexが見つからずエラーになる)ようにする。
            hq_choice_ids = list(hq_options.keys()) + (
                [u.headquarters_id] if u.headquarters_id is not None and u.headquarters_id not in hq_options else []
            )
            branch_choice_ids = list(branch_options.keys()) + (
                [u.branch_id] if u.branch_id is not None and u.branch_id not in branch_options else []
            )
            new_hq = c3.selectbox(
                "統括部門",
                options=[None] + hq_choice_ids,
                format_func=lambda i: "未設定" if i is None else hq_labels_all[i],
                index=(0 if u.headquarters_id is None else hq_choice_ids.index(u.headquarters_id) + 1),
                key=f"hq_{u.id}",
                disabled=not u.active,
            )
            new_branch = c4.selectbox(
                "拠点(部門名称)",
                options=[None] + branch_choice_ids,
                format_func=lambda i: "未設定" if i is None else branch_labels_all[i],
                index=(0 if u.branch_id is None else branch_choice_ids.index(u.branch_id) + 1),
                key=f"branch_{u.id}",
                disabled=not u.active,
            )
            new_region = c5.selectbox(
                "地域区分",
                options=[None] + list(region_options.keys()),
                format_func=lambda i: "未設定" if i is None else region_options[i],
                index=(0 if u.region_id is None else list(region_options.keys()).index(u.region_id) + 1),
                key=f"region_{u.id}",
                disabled=not u.active,
            )

            if u.role != ROLE_MANAGER:
                mgrs = managers_by_branch.get(u.branch_id, [])
                if u.branch_id is None:
                    st.caption("承認可能なマネージャー: 拠点未設定のため判定できません")
                elif mgrs:
                    st.caption(f"承認可能なマネージャー: 有({', '.join(m.display_name or m.username for m in mgrs)})")
                else:
                    st.caption("承認可能なマネージャー: 無(この拠点にマネージャーがいません)")

            b1, b2, b3 = st.columns(3)
            toggle_label = "無効化する" if u.active else "有効化する"
            if b1.button(toggle_label, key=f"toggle_active_{u.id}"):
                u.active = not u.active
                session.commit()
                st.rerun()
            if b2.button("保存", key=f"save_user_{u.id}", disabled=not u.active):
                u.role = new_role
                u.headquarters_id = new_hq
                u.branch_id = new_branch
                u.region_id = new_region
                session.commit()
                st.success("保存しました。")
                st.rerun()
            new_pw = b3.text_input("新しいパスワード", type="password", key=f"pw_{u.id}", disabled=not u.active)
            if new_pw and st.button("パスワードを再設定", key=f"reset_pw_{u.id}", disabled=not u.active):
                u.password_hash = hash_password(new_pw)
                session.commit()
                st.success("パスワードを再設定しました。")

# ---------------------------------------------------------------
# 組織属性マスタ(統括部門・拠点・地域区分)
# ---------------------------------------------------------------
with tab_org:
    st.caption(
        "統廃合・組織変更で部門を統合したいときは「統合」を使ってください。統合すると、"
        "所属していたユーザーは統合先へ自動的に付け替わり、統合元の名称は「統合済み」として"
        "履歴に残ります(行自体は削除しません)。過去に作成済みの見積は、作成時点の部門名を"
        "そのまま保持しているため、統合・名称変更を行っても表示内容は変わりません。"
    )
    col_hq, col_branch, col_region = st.columns(3)
    with col_hq:
        st.subheader("統括部門名称マスタ")
        with st.form("new_hq_form", clear_on_submit=True):
            name = st.text_input("新しい統括部門名称")
            if st.form_submit_button("追加", type="primary"):
                existing = {h.name for h in headquarters}
                if not name:
                    st.error("名称を入力してください。")
                elif name in existing:
                    st.error(f"「{name}」は既に登録されています。")
                else:
                    session.add(HeadquartersMaster(name=name))
                    session.commit()
                    st.rerun()
        active_hq = [h for h in headquarters if h.active]
        for h in active_hq:
            hc1, hc2 = st.columns([3, 2])
            hc1.write(f"- {h.name}")
            merge_targets = {o.id: o.name for o in active_hq if o.id != h.id}
            if merge_targets:
                target_id = hc2.selectbox(
                    "統合先", options=list(merge_targets.keys()), format_func=lambda i: merge_targets[i],
                    key=f"hq_merge_target_{h.id}", label_visibility="collapsed",
                )
                if hc2.button("この統括部門を統合", key=f"hq_merge_{h.id}"):
                    target = session.get(HeadquartersMaster, target_id)
                    for u in session.execute(select(User).where(User.headquarters_id == h.id)).scalars().all():
                        u.headquarters_id = target.id
                    h.active = False
                    h.merged_into_id = target.id
                    h.merged_at = dt.datetime.utcnow()
                    session.commit()
                    st.success(f"「{h.name}」を「{target.name}」に統合しました。")
                    st.rerun()
        merged_hq = [h for h in headquarters if not h.active]
        if merged_hq:
            with st.expander(f"統合済み({len(merged_hq)}件)"):
                for h in merged_hq:
                    st.caption(f"{h.name} → {h.merged_into.name if h.merged_into else '(不明)'}({h.merged_at})")
    with col_branch:
        st.subheader("拠点名称マスタ(部門名称)")
        with st.form("new_branch_form", clear_on_submit=True):
            name = st.text_input("新しい拠点名称")
            if st.form_submit_button("追加", type="primary"):
                existing = {b.name for b in branches}
                if not name:
                    st.error("名称を入力してください。")
                elif name in existing:
                    st.error(f"「{name}」は既に登録されています。")
                else:
                    session.add(BranchMaster(name=name))
                    session.commit()
                    st.rerun()
        active_branches = [b for b in branches if b.active]
        for b in active_branches:
            bc1, bc2 = st.columns([3, 2])
            bc1.write(f"- {b.name}")
            merge_targets = {o.id: o.name for o in active_branches if o.id != b.id}
            if merge_targets:
                target_id = bc2.selectbox(
                    "統合先", options=list(merge_targets.keys()), format_func=lambda i: merge_targets[i],
                    key=f"branch_merge_target_{b.id}", label_visibility="collapsed",
                )
                if bc2.button("この拠点を統合", key=f"branch_merge_{b.id}"):
                    target = session.get(BranchMaster, target_id)
                    for u in session.execute(select(User).where(User.branch_id == b.id)).scalars().all():
                        u.branch_id = target.id
                    b.active = False
                    b.merged_into_id = target.id
                    b.merged_at = dt.datetime.utcnow()
                    session.commit()
                    st.success(f"「{b.name}」を「{target.name}」に統合しました。")
                    st.rerun()
        merged_branches = [b for b in branches if not b.active]
        if merged_branches:
            with st.expander(f"統合済み({len(merged_branches)}件)"):
                for b in merged_branches:
                    st.caption(f"{b.name} → {b.merged_into.name if b.merged_into else '(不明)'}({b.merged_at})")
    with col_region:
        st.subheader("地域区分マスタ")
        with st.form("new_region_form", clear_on_submit=True):
            name = st.text_input("新しい地域区分名")
            if st.form_submit_button("追加", type="primary"):
                existing = {r.name for r in regions}
                if not name:
                    st.error("名称を入力してください。")
                elif name in existing:
                    st.error(f"「{name}」は既に登録されています。")
                else:
                    session.add(RegionMaster(name=name))
                    session.commit()
                    st.rerun()
        for r in regions:
            st.write(f"- {r.name}")

# ---------------------------------------------------------------
# エラーログ
# ---------------------------------------------------------------
with tab_logs:
    st.subheader("エラーログ(新しい順・直近200件)")
    logs = session.execute(select(ErrorLog).order_by(ErrorLog.occurred_at.desc()).limit(200)).scalars().all()
    if not logs:
        st.info("記録されたエラーはありません。")
    for log in logs:
        with st.expander(f"{log.occurred_at} / {log.page} / {log.user.display_name if log.user else '(未ログイン)'}"):
            st.code(log.message)

session.close()
