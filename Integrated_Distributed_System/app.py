from __future__ import annotations

import time

import streamlit as st

from core.protocol import request

from core.node_manager import start_all, start_node, stop_node



st.set_page_config(page_title="Distributed Systems Lab", page_icon="🌐",

                   layout="wide", initial_sidebar_state="expanded")



# ---- visual theme ----

st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }

.stApp { background: radial-gradient(circle at 8% 0%, #14243b 0, #0b1220 34%, #080d17 100%); color: #edf3ff; }

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] { background: #0c1524; border-right: 1px solid #1e3048; }

.block-container { padding-top: 2rem; max-width: 1450px; }

.hero { padding: 26px 30px; border: 1px solid #28415e; border-radius: 22px;

        background: linear-gradient(120deg, rgba(21,49,76,.95), rgba(13,25,43,.92));

        box-shadow: 0 18px 55px rgba(0,0,0,.22); margin-bottom: 22px; }

.eyebrow { color: #66d9c2; letter-spacing: .18em; font-size: .72rem; font-weight: 800; }

.hero h1 { color: #f5f8ff; font-size: 2.2rem; margin: 8px 0 4px; font-weight: 800; }

.hero p { color: #a9bad0; margin: 0; font-size: 1rem; }

.metric { background: #111e30; border: 1px solid #263c56; border-radius: 16px; padding: 17px 19px; min-height: 105px; }

.metric .label { color: #91a8c2; font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }

.metric .value { color: #f5f8ff; font-size: 1.85rem; font-weight: 800; margin-top: 4px; }

.node-card { background: #111e30; border: 1px solid #263c56; border-radius: 16px; padding: 17px; }

.online { color: #64e3b4; font-weight: 800; }

.offline { color: #ff7e88; font-weight: 800; }

.small-muted { color: #91a8c2; font-size: .82rem; }

div[data-testid="stTabs"] button { color: #a9bad0; }

div[data-testid="stTabs"] button[aria-selected="true"] { color: #67dec5; }

.stButton > button[kind="primary"] { background: #19a98f; border: 0; color: #061a19; font-weight: 800; border-radius: 10px; }

.stButton > button { border-radius: 10px; }

div[data-testid="stForm"] { background: #111e30; padding: 18px; border: 1px solid #263c56; border-radius: 16px; }

code, pre { font-family: 'DM Mono', monospace; }

</style>

""", unsafe_allow_html=True)



if "last_result" not in st.session_state:

    st.session_state.last_result = None

if "notice" not in st.session_state:

    st.session_state.notice = ""



def safe_request(node_id, payload, timeout=2.0):

    try:

        return request(node_id, payload, timeout=timeout)

    except Exception as exc:

        return {"ok": False, "error": str(exc)}



def get_status(node_id):

    result = safe_request(node_id, {"action": "PING"})

    return result if result.get("ok") else {"ok": False, "node_id": node_id,

                                             "clock": "—", "records": "—",

                                             "error": result.get("error", "Offline")}



def metric(label, value, note=""):

    st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div><div class="small-muted">{note}</div></div>', unsafe_allow_html=True)



# Sidebar controls

with st.sidebar:

    st.markdown("## 🌐 Control Center")

    st.caption("LOCAL DISTRIBUTED CLUSTER")

    if st.button("▶ Start all nodes", use_container_width=True, type="primary"):

        results = start_all()

        st.session_state.notice = " | ".join(message for _, message in results)

        st.rerun()

        # Node controls
    node_rows = [
        (1, "N1"),
        (2, "N2"),
        (3, "N3")
    ]

    for node_id, node_name in node_rows:
        start_col, stop_col = st.columns(2)

        with start_col:
            if st.button(
                f"▶ Start {node_name}",
                use_container_width=True,
                key=f"start_node_{node_id}"
            ):
                result = start_node(node_id)
                st.session_state.notice = result[1]
                st.rerun()

        with stop_col:
            if st.button(
                f"■ Stop {node_name}",
                use_container_width=True,
                key=f"stop_node_{node_id}"
            ):
                result = stop_node(node_id)
                st.session_state.notice = result[1]
                st.rerun()

    st.divider()

    st.markdown("**Network configuration**")

    st.code("N1  127.0.0.1:8101\nN2  127.0.0.1:8102\nN3  127.0.0.1:8103", language="text")

    st.caption("Node 1 coordinates writes. Nodes 2 and 3 maintain replicas.")

    if st.button("↻ Refresh dashboard", use_container_width=True):

        st.rerun()



statuses = {i: get_status(i) for i in (1, 2, 3)}

online_count = sum(1 for s in statuses.values() if s.get("ok"))



st.markdown("""

<div class="hero">

  <div class="eyebrow">DISTRIBUTED SYSTEMS • 5TH SEMESTER PROJECT</div>

  <h1>Integrated Distributed System</h1>

  <p>Live communication · Lamport logical clocks · replicated student records · fault recovery</p>

</div>

""", unsafe_allow_html=True)



if st.session_state.notice:

    st.info(st.session_state.notice)

    st.session_state.notice = ""



# Overview metrics

m1, m2, m3, m4 = st.columns(4)

with m1: metric("Cluster health", f"{online_count}/3", "nodes online")

with m2: metric("Primary node", "NODE 1", "write coordinator")

with m3: metric("Replication", "ACTIVE" if online_count > 1 else "WAITING", "peer updates on each write")

with m4:

    max_clock = max([s["clock"] for s in statuses.values() if s.get("ok")], default=0)

    metric("Highest observed clock", max_clock, "Lamport logical time")



st.markdown("### Node cluster")

node_cols = st.columns(3)

for idx, node_id in enumerate((1, 2, 3)):

    status = statuses[node_id]

    with node_cols[idx]:

        state_class = "online" if status.get("ok") else "offline"

        state_text = "● ONLINE" if status.get("ok") else "● OFFLINE"

        st.markdown(

            f'<div class="node-card"><div style="display:flex;justify-content:space-between">'

            f'<b>NODE {node_id}</b><span class="{state_class}">{state_text}</span></div>'

            f'<h2 style="margin:14px 0 2px;color:#f4f7ff">{status.get("clock","—")}</h2>'

            f'<div class="small-muted">Lamport clock</div>'

            f'<div style="margin-top:12px;color:#b7c8dc">Records: <b>{status.get("records","—")}</b></div>'

            f'<div class="small-muted">127.0.0.1:{8100+node_id}</div></div>',

            unsafe_allow_html=True

        )

        if not status.get("ok"):

            st.caption("Start this node from the sidebar.")



tabs = st.tabs(["🗂 Student records", "⏱ Lamport clocks & events", "🔁 Replication & recovery", "📘 How it works"])



with tabs[0]:

    left, right = st.columns([1, 1.35], gap="large")

    with left:

        st.markdown("#### Create / update a record")

        with st.form("student_write_form", clear_on_submit=True):

            student_id = st.text_input("Student ID", placeholder="e.g. 101")

            name = st.text_input("Student name", placeholder="e.g. Asha Kumar")

            department = st.selectbox("Department", ["AIML", "CSE", "ISE", "ECE", "EEE", "Mechanical", "Civil", "Other"])

            submitted = st.form_submit_button("Save and replicate", type="primary", use_container_width=True)

        if submitted:

            if not student_id.strip() or not name.strip():

                st.error("Please enter both Student ID and student name.")

            elif not statuses[1].get("ok"):

                st.error("Primary Node 1 is offline. Start Node 1 before writing.")

            else:

                result = safe_request(1, {"action": "CLIENT_WRITE", "operation": "ADD",

                                          "student_id": student_id.strip(), "name": name.strip(),

                                          "department": department}, timeout=8)

                st.session_state.last_result = result

                if result.get("ok"):

                    st.success(f"Write committed at Node 1 with Lamport timestamp {result['clock']}.")

                else:

                    st.error(result.get("error", "Write failed."))

                st.rerun()



        st.markdown("#### Delete a record")

        with st.form("delete_form"):

            delete_id = st.text_input("Student ID to delete")

            delete_submitted = st.form_submit_button("Delete and replicate")

        if delete_submitted:

            if not delete_id.strip():

                st.warning("Enter a Student ID.")

            else:

                result = safe_request(1, {"action": "CLIENT_WRITE", "operation": "DELETE",

                                          "student_id": delete_id.strip()}, timeout=8)

                st.session_state.last_result = result

                if result.get("ok"):

                    st.success(f"Delete event timestamp: {result['clock']}")

                else:

                    st.error(result.get("error", "Delete failed."))

                st.rerun()



    with right:

        st.markdown("#### Replication result")

        result = st.session_state.last_result

        if result and result.get("ok"):

            st.markdown(f"**Event:** `{result.get('event_id','')[:12]}…`")

            st.markdown(f"**Primary Lamport timestamp:** `{result.get('clock')}`")

            for replica in result.get("replicas", []):

                if replica.get("ok"):

                    st.success(f"Node {replica['node_id']}: {replica.get('message','Replicated')}")

                else:

                    st.error(f"Node {replica['node_id']}: replication pending — {replica.get('message','offline')}")

        elif result:

            st.error(result.get("error", "Last operation failed."))

        else:

            st.info("Submit a record to see its replication acknowledgements here.")



        st.markdown("#### Current records by node")

        selected_node = st.selectbox("View replica", [1, 2, 3], format_func=lambda n: f"Node {n}")

        state = safe_request(selected_node, {"action": "GET_STATE"})

        if state.get("ok"):

            visible = [r for r in state["records"] if not r.get("deleted")]

            if visible:

                import pandas as pd

                st.dataframe(pd.DataFrame([{

                    "Student ID": r["student_id"], "Name": r["name"],

                    "Department": r["department"], "Version clock": r["version_clock"],

                    "Origin node": r["version_node"]

                } for r in visible]), use_container_width=True, hide_index=True)

            else:

                st.info("No active records in this replica.")

        else:

            st.warning(f"Node {selected_node} is unavailable.")



with tabs[1]:

    st.markdown("#### Logical clock comparison")

    clock_rows = []

    for n, s in statuses.items():

        clock_rows.append({"Node": f"Node {n}", "Status": "ONLINE" if s.get("ok") else "OFFLINE",

                           "Lamport clock": s.get("clock", "—"), "Active records": s.get("records", "—")})

    st.dataframe(clock_rows, use_container_width=True, hide_index=True)

    st.caption("A message receive event updates the receiver clock using max(local clock, sender timestamp) + 1.")

    event_node = st.selectbox("Show event log for", [1, 2, 3], key="event_node")

    events_result = safe_request(event_node, {"action": "GET_EVENTS", "limit": 80})

    if events_result.get("ok") and events_result.get("events"):

        import pandas as pd

        event_data = [{

            "Event": e["event_type"], "Description": e["description"],

            "Lamport time": e["lamport_clock"], "Wall time (display only)": e["created_at"]

        } for e in events_result["events"]]

        st.dataframe(pd.DataFrame(event_data), use_container_width=True, hide_index=True)

    elif not events_result.get("ok"):

        st.warning(f"Node {event_node} is offline.")

    else:

        st.info("No events recorded yet. Start the nodes and perform an operation.")



with tabs[2]:

    st.markdown("#### Replica recovery")

    st.write("If a node was offline while writes occurred, restart it and synchronize it from the available replicas.")

    recovery_node = st.selectbox("Node to recover", [2, 3], key="recovery_node")

    if st.button("Synchronize selected node", type="primary"):

        target_status = get_status(recovery_node)

        if not target_status.get("ok"):

            st.error(f"Node {recovery_node} is offline. Start it first from the sidebar.")

        else:

            source_ids = [i for i in (1, 2, 3) if i != recovery_node and get_status(i).get("ok")]

            if not source_ids:

                st.error("No online source replica is available.")

            else:

                # Merge records from each available source. Version tuple resolves stale copies.

                synced = 0

                errors = []

                for source_id in source_ids:

                    source_state = safe_request(source_id, {"action": "GET_STATE"})

                    if not source_state.get("ok"):

                        errors.append(f"Could not read Node {source_id}.")

                        continue

                    for record in source_state.get("records", []):

                        applied = safe_request(recovery_node, {

                            "action": "SYNC_APPLY", "record": record,

                            "sender_clock": source_state.get("clock", 0)

                        })

                        if applied.get("ok") and applied.get("changed"):

                            synced += 1

                        elif not applied.get("ok"):

                            errors.append(applied.get("error", "sync failed"))

                if errors:

                    st.warning("Recovery completed with warnings: " + "; ".join(errors[:3]))

                else:

                    st.success(f"Recovery complete. {synced} record version(s) applied to Node {recovery_node}.")

                st.rerun()



    st.markdown("#### Failure simulation")

    st.write("Use the sidebar to stop Node 2, perform a write, restart Node 2, and recover it here.")

    st.warning("This demo uses a primary-write design. If Node 1 is offline, new writes are unavailable; existing replicas remain readable.")



with tabs[3]:

    st.markdown("#### Architecture")

    st.code("""

          Streamlit Dashboard

                  |

             TCP / JSON

                  |

             Node 1 (Primary)

              /          \

         TCP replication  TCP replication

            /                \

       Node 2               Node 3

       Replica              Replica

       SQLite               SQLite

    """, language="text")

    st.markdown("#### Lamport logical clock rules")

    st.latex(r"L := L + 1")

    st.write("For every local event, the node increments its own logical clock.")

    st.latex(r"L := **\**&#x6D;ax(L, T) + 1")

    st.write("When a node receives a message carrying timestamp T, it sets its clock to the maximum of its current value and T, then increments it.")

    st.markdown("#### Replication flow")

    st.markdown("""

    1. Dashboard sends a write request to primary Node 1.

    2. Node 1 increments its clock, stores the version in its local SQLite database and creates an event ID.

    3. Node 1 sends the record and its Lamport timestamp to Nodes 2 and 3.

    4. Each receiving replica updates its clock using the receive rule, applies the newest record version and sends an acknowledgement.

    5. If a replica was offline, the recovery tab merges record versions from available nodes.

    """)

    st.markdown("#### Important limitations")

    st.info("This is an academic prototype. It demonstrates message passing, logical clocks, replication and recovery; it does not implement consensus, quorum commits, secure authentication or production-grade conflict resolution.")



st.markdown("<div style='text-align:center;color:#7187a2;padding:24px 0 8px;font-size:.8rem'>DISTRIBUTED SYSTEMS LAB · PYTHON · TCP SOCKETS · SQLITE · STREAMLIT</div>", unsafe_allow_html=True)
