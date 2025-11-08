#!/usr/bin/env python3
"""
ICS Anomaly Detection Dashboard
Interactive dashboard for monitoring and executing attacks
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="ICS Anomaly Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoints
DETECTION_API = "http://ics-detection-api:8000"
ATTACK_API = "http://ics-attacker:8002"

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #FF4B4B;
    }
    .attack-button {
        width: 100%;
        margin: 5px 0;
    }
    .status-running {
        color: #FFA500;
        font-weight: bold;
    }
    .status-completed {
        color: #00FF00;
        font-weight: bold;
    }
    .status-healthy {
        color: #00FF00;
    }
    .status-warning {
        color: #FFA500;
    }
    </style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if both APIs are accessible"""
    detection_ok = False
    attack_ok = False
    
    try:
        response = requests.get(f"{DETECTION_API}/health", timeout=2)
        detection_ok = response.status_code == 200
    except:
        pass
    
    try:
        response = requests.get(f"{ATTACK_API}/health", timeout=2)
        attack_ok = response.status_code == 200
    except:
        pass
    
    return detection_ok, attack_ok

def get_system_status():
    """Get detection system status"""
    try:
        response = requests.get(f"{DETECTION_API}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to get system status: {e}")
    return None

def get_current_anomalies(limit=20):
    """Get recent anomalies"""
    try:
        response = requests.get(f"{DETECTION_API}/anomalies/current?limit={limit}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to get anomalies: {e}")
    return None

def get_anomaly_stats():
    """Get anomaly statistics"""
    try:
        response = requests.get(f"{DETECTION_API}/anomalies/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return None
    return None

def get_available_attacks():
    """Get available attack types"""
    try:
        response = requests.get(f"{ATTACK_API}/attacks/available", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to get attacks: {e}")
    return None

def execute_attack(attack_type, target, duration):
    """Execute an attack"""
    try:
        payload = {
            "attack_type": attack_type,
            "target": target,
            "duration": duration
        }
        response = requests.post(f"{ATTACK_API}/attacks/execute", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Attack failed: {response.text}")
    except Exception as e:
        st.error(f"Failed to execute attack: {e}")
    return None

def get_attack_history():
    """Get attack execution history"""
    try:
        response = requests.get(f"{ATTACK_API}/attacks/history", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return None
    return None

# Title and header
st.title("🛡️ ICS Anomaly Detection Dashboard")
st.markdown("**Real-time monitoring and attack scenario testing**")

# Check API health
detection_ok, attack_ok = check_api_health()

# Status indicators in sidebar
with st.sidebar:
    st.header("System Status")
    
    col1, col2 = st.columns(2)
    with col1:
        if detection_ok:
            st.markdown("🟢 **Detection API**")
        else:
            st.markdown("🔴 **Detection API**")
    
    with col2:
        if attack_ok:
            st.markdown("🟢 **Attack API**")
        else:
            st.markdown("🔴 **Attack API**")
    
    st.divider()
    
    # Auto-refresh control
    st.subheader("Auto-Refresh")
    auto_refresh = st.checkbox("Enable", value=True)
    if auto_refresh:
        refresh_interval = st.slider("Interval (seconds)", 5, 60, 10)
        st.info(f"Refreshing every {refresh_interval}s")

# Main content area
tab1, tab2, tab3 = st.tabs(["📊 Monitoring", "⚔️ Attack Control", "📈 Analytics"])

with tab1:
    st.header("Real-Time Anomaly Monitoring")
    
    # System metrics
    status = get_system_status()
    if status:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Records Processed",
                f"{status['records_processed']:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Anomalies Detected",
                status['anomalies_detected'],
                delta=None,
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "Current Window",
                status['current_window'] if status['current_window'] else "N/A"
            )
        
        with col4:
            detector_status = "🟢 Running" if status['detector_running'] else "🔴 Stopped"
            st.metric("Detector", detector_status)
        
        st.caption(f"Last check: {status.get('last_check', 'N/A')}")
    else:
        st.warning("Unable to connect to detection API")
    
    st.divider()
    
    # Recent anomalies
    st.subheader("Recent Anomalies")
    
    anomalies_data = get_current_anomalies(limit=20)
    if anomalies_data and anomalies_data['count'] > 0:
        df = pd.DataFrame(anomalies_data['anomalies'])
        
        # Display count
        st.success(f"**{anomalies_data['count']} anomalies detected**")
        
        # Show dataframe
        display_cols = ['detected_at', 'src', 'dst', 'anomaly_score', 'read_count_sum', 'registers_accessed']
        available_cols = [col for col in display_cols if col in df.columns]
        
        st.dataframe(
            df[available_cols].sort_values('detected_at', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Anomaly score distribution
        if len(df) > 1:
            fig = px.histogram(
                df,
                x='anomaly_score',
                nbins=20,
                title="Anomaly Score Distribution",
                labels={'anomaly_score': 'Anomaly Score', 'count': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("No anomalies detected yet. Execute an attack to test detection!")

with tab2:
    st.header("Attack Control Panel")
    
    if not attack_ok:
        st.error("❌ Attack API is not available. Start the attacker container.")
    else:
        attacks_info = get_available_attacks()
        
        if attacks_info:
            attacks = attacks_info['attacks']
            targets = attacks_info['targets']
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Launch Attack")
                
                # Attack selection
                attack_type = st.selectbox(
                    "Attack Type",
                    options=list(attacks.keys()),
                    format_func=lambda x: f"{attacks[x]['name']} - {attacks[x]['description']}"
                )
                
                # Show expected detection
                if attack_type:
                    st.info(f"**Expected Detection:** {attacks[attack_type]['expected_detection']}")
                
                # Target selection
                target = st.selectbox(
                    "Target PLC",
                    options=list(targets.keys()),
                    format_func=lambda x: f"{x.upper()} ({targets[x]})"
                )
                
                # Duration
                duration = st.slider("Duration (seconds)", 10, 120, 30)
                
                # Launch button
                if st.button("🚀 Launch Attack", type="primary", use_container_width=True):
                    with st.spinner("Launching attack..."):
                        result = execute_attack(attack_type, target, duration)
                        if result:
                            st.success(f"✅ Attack launched: {result['attack_id']}")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
            
            with col2:
                st.subheader("Available Attacks")
                for attack_id, attack_info in attacks.items():
                    with st.expander(attack_info['name']):
                        st.markdown(f"**Description:** {attack_info['description']}")
                        st.markdown(f"**Detection:** {attack_info['expected_detection']}")
            
            st.divider()
            
            # Attack history
            st.subheader("Attack History")
            history = get_attack_history()
            
            if history and history['count'] > 0:
                attacks_list = history['attacks']
                
                # Reverse to show most recent first
                attacks_list = sorted(attacks_list, key=lambda x: x['started_at'], reverse=True)
                
                for attack in attacks_list[:10]:  # Show last 10
                    with st.container():
                        cols = st.columns([3, 2, 2, 1])
                        
                        with cols[0]:
                            attack_name = attacks.get(attack['attack_type'], {}).get('name', attack['attack_type'])
                            st.markdown(f"**{attack_name}**")
                            st.caption(f"Target: {attack['target']}")
                        
                        with cols[1]:
                            st.caption(f"Started: {attack['started_at'][:19]}")
                        
                        with cols[2]:
                            status = attack['status']
                            if status == 'running':
                                st.markdown('<span class="status-running">🔄 Running</span>', unsafe_allow_html=True)
                            elif status == 'completed':
                                st.markdown('<span class="status-completed">✅ Completed</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f"❌ {status.capitalize()}")
                        
                        with cols[3]:
                            if attack['completed_at']:
                                start = datetime.fromisoformat(attack['started_at'])
                                end = datetime.fromisoformat(attack['completed_at'])
                                duration = (end - start).total_seconds()
                                st.caption(f"{duration:.1f}s")
                        
                        st.divider()
            else:
                st.info("No attacks executed yet")

with tab3:
    st.header("Analytics & Statistics")
    
    stats = get_anomaly_stats()
    
    if stats and stats.get('total_anomalies', 0) > 0:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Anomalies", stats['total_anomalies'])
        
        with col2:
            st.metric("Data Files", stats['files'])
        
        with col3:
            score_dist = stats.get('score_distribution', {})
            if score_dist:
                st.metric("Avg Anomaly Score", f"{score_dist.get('mean', 0):.3f}")
        
        st.divider()
        
        # Score distribution
        score_dist = stats.get('score_distribution', {})
        if score_dist:
            st.subheader("Score Distribution")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Min Score", f"{score_dist.get('min', 0):.3f}")
                st.metric("Median Score", f"{score_dist.get('median', 0):.3f}")
            with col2:
                st.metric("Max Score", f"{score_dist.get('max', 0):.3f}")
                st.metric("Std Dev", f"{score_dist.get('std', 0):.3f}")
        
        st.divider()
        
        # By source
        by_source = stats.get('by_source', {})
        if by_source:
            st.subheader("Anomalies by Source IP")
            source_df = pd.DataFrame([
                {'Source IP': k, 'Count': v} for k, v in by_source.items()
            ])
            fig = px.bar(source_df, x='Source IP', y='Count', title="Anomalies by Source")
            st.plotly_chart(fig, use_container_width=True)
        
        # By destination
        by_dest = stats.get('by_destination', {})
        if by_dest:
            st.subheader("Anomalies by Destination IP (PLC)")
            dest_df = pd.DataFrame([
                {'Destination IP': k, 'Count': v} for k, v in by_dest.items()
            ])
            fig = px.bar(dest_df, x='Destination IP', y='Count', title="Anomalies by Destination")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No anomaly statistics available yet. Execute attacks to generate data!")
        
        # Show feature information
        st.subheader("Detection Features")
        st.markdown("""
        The system monitors **28 behavioral features** including:
        - Register value patterns (mean, std, range, changes)
        - Read/write frequencies and rates
        - Timing patterns (inter-arrival times)
        - Statistical outliers and entropy
        - Temporal deviations (rolling windows)
        """)

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
