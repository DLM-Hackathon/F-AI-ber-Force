"""
Smart Dispatch Optimization Dashboard
Interactive web application to visualize dispatch optimization results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="Smart Dispatch Optimization",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    h1 {
        color: #1f77b4;
    }
    h2 {
        color: #2c3e50;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and header
st.title("🚚 Smart Dispatch Optimization Dashboard")
st.markdown("### ML-Based Technician Assignment System")
st.markdown("---")

# Load data
@st.cache_data
def load_data():
    """Load the optimized dispatch results"""
    try:
        # Try to load the results file
        if os.path.exists('optimized_dispatch_results.csv'):
            df = pd.read_csv('optimized_dispatch_results.csv')
            return df, None
        else:
            return None, "⚠️ Results file not found. Please run dispatch_agent.py first."
    except Exception as e:
        return None, f"⚠️ Error loading data: {str(e)}"

df, error = load_data()

if error:
    st.error(error)
    st.info("Run the dispatch agent first: `python dispatch_agent.py`")
    st.stop()

# Sidebar - Filters and Controls
st.sidebar.header("🎛️ Filters & Controls")

# City filter
cities = ['All'] + sorted(df['City'].dropna().unique().tolist())
selected_city = st.sidebar.selectbox("Select City", cities)

# Required skill filter
skills = ['All'] + sorted(df['Required_skill'].dropna().unique().tolist())
selected_skill = st.sidebar.selectbox("Select Required Skill", skills)

# Fallback level filter
fallback_levels = ['All'] + sorted(df['Fallback_level'].dropna().unique().tolist())
selected_fallback = st.sidebar.selectbox("Select Fallback Level", fallback_levels)

# Assignment status filter
assignment_status = st.sidebar.radio(
    "Assignment Status",
    ["All", "Assigned", "Unassigned"]
)

# Apply filters
filtered_df = df.copy()

if selected_city != 'All':
    filtered_df = filtered_df[filtered_df['City'] == selected_city]

if selected_skill != 'All':
    filtered_df = filtered_df[filtered_df['Required_skill'] == selected_skill]

if selected_fallback != 'All':
    filtered_df = filtered_df[filtered_df['Fallback_level'] == selected_fallback]

if assignment_status == "Assigned":
    filtered_df = filtered_df[filtered_df['Optimized_technician_id'].notna()]
elif assignment_status == "Unassigned":
    filtered_df = filtered_df[filtered_df['Optimized_technician_id'].isna()]

# Display filter info
st.sidebar.markdown("---")
st.sidebar.metric("Filtered Dispatches", len(filtered_df))
st.sidebar.metric("Total Dispatches", len(df))

# Main dashboard content
if len(filtered_df) == 0:
    st.warning("No dispatches match the selected filters.")
    st.stop()

# ============================================================
# KEY METRICS OVERVIEW
# ============================================================
st.header("📊 Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

# Calculate metrics
assigned_count = filtered_df['Optimized_technician_id'].notna().sum()
unassigned_count = filtered_df['Optimized_technician_id'].isna().sum()
assignment_rate = (assigned_count / len(filtered_df)) * 100

avg_initial_success = filtered_df['Initial_success_prob'].mean()
avg_optimized_success = filtered_df['Predicted_success_prob'].mean()
success_improvement = avg_optimized_success - avg_initial_success

avg_initial_distance = filtered_df['Initial_distance_km'].mean()
avg_optimized_distance = filtered_df['Optimized_distance_km'].mean()
distance_reduction = avg_initial_distance - avg_optimized_distance

total_distance_saved = filtered_df['Distance_change_km'].sum()
fuel_savings = abs(total_distance_saved) * 0.50  # $0.50 per km

with col1:
    st.metric(
        "Assignment Rate",
        f"{assignment_rate:.1f}%",
        f"{assigned_count} / {len(filtered_df)}"
    )

with col2:
    st.metric(
        "Avg Success Probability",
        f"{avg_optimized_success:.3f}",
        f"{success_improvement:+.3f}",
        delta_color="normal" if success_improvement >= 0 else "inverse"
    )

with col3:
    st.metric(
        "Avg Distance (km)",
        f"{avg_optimized_distance:.1f}",
        f"{-distance_reduction:+.1f} km",
        delta_color="inverse" if distance_reduction > 0 else "normal"
    )

with col4:
    st.metric(
        "Total Distance Saved",
        f"{abs(total_distance_saved):.0f} km",
        f"${fuel_savings:.0f} saved"
    )

with col5:
    improvement_rate = (filtered_df['Success_prob_improvement'] > 0).sum()
    improvement_pct = (improvement_rate / len(filtered_df)) * 100
    st.metric(
        "Improved Assignments",
        f"{improvement_rate}",
        f"{improvement_pct:.1f}%"
    )

st.markdown("---")

# ============================================================
# DETAILED COMPARISON CHARTS
# ============================================================
st.header("📈 Detailed Performance Analysis")

# Create tabs for different visualizations
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", "🎯 Success Probability", "📍 Distance Analysis", 
    "⚖️ Workload Balance", "🔍 Individual Dispatches"
])

# TAB 1: Overview Comparisons
with tab1:
    st.subheader("Initial vs Optimized Comparison")
    
    # Create comparison metrics
    col1, col2 = st.columns(2)
    
    with col1:
        # Success Probability Comparison
        fig_success = go.Figure()
        
        fig_success.add_trace(go.Box(
            y=filtered_df['Initial_success_prob'],
            name='Initial',
            marker_color='lightblue',
            boxmean='sd'
        ))
        
        fig_success.add_trace(go.Box(
            y=filtered_df['Predicted_success_prob'],
            name='Optimized',
            marker_color='lightgreen',
            boxmean='sd'
        ))
        
        fig_success.update_layout(
            title='Success Probability Distribution',
            yaxis_title='Success Probability',
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig_success, use_container_width=True)
    
    with col2:
        # Distance Comparison
        fig_distance = go.Figure()
        
        fig_distance.add_trace(go.Box(
            y=filtered_df['Initial_distance_km'],
            name='Initial',
            marker_color='salmon',
            boxmean='sd'
        ))
        
        fig_distance.add_trace(go.Box(
            y=filtered_df['Optimized_distance_km'],
            name='Optimized',
            marker_color='lightcoral',
            boxmean='sd'
        ))
        
        fig_distance.update_layout(
            title='Distance Distribution (km)',
            yaxis_title='Distance (km)',
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig_distance, use_container_width=True)
    
    # Improvement breakdown
    st.subheader("Improvement Breakdown")
    
    improved = (filtered_df['Success_prob_improvement'] > 0).sum()
    worse = (filtered_df['Success_prob_improvement'] < 0).sum()
    unchanged = (filtered_df['Success_prob_improvement'] == 0).sum()
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Improved', 'Worse', 'Unchanged'],
        values=[improved, worse, unchanged],
        hole=.3,
        marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
    )])
    
    fig_pie.update_layout(
        title='Assignment Outcome Distribution',
        height=400
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

# TAB 2: Success Probability Analysis
with tab2:
    st.subheader("Success Probability Deep Dive")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram of success probability improvement
        fig_hist = px.histogram(
            filtered_df,
            x='Success_prob_improvement',
            nbins=50,
            title='Success Probability Improvement Distribution',
            labels={'Success_prob_improvement': 'Improvement', 'count': 'Number of Dispatches'},
            color_discrete_sequence=['#3498db']
        )
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Success probability by skill
        skill_success = filtered_df.groupby('Required_skill').agg({
            'Initial_success_prob': 'mean',
            'Predicted_success_prob': 'mean'
        }).reset_index()
        
        fig_skill = go.Figure()
        fig_skill.add_trace(go.Bar(
            x=skill_success['Required_skill'],
            y=skill_success['Initial_success_prob'],
            name='Initial',
            marker_color='lightblue'
        ))
        fig_skill.add_trace(go.Bar(
            x=skill_success['Required_skill'],
            y=skill_success['Predicted_success_prob'],
            name='Optimized',
            marker_color='lightgreen'
        ))
        
        fig_skill.update_layout(
            title='Average Success Probability by Skill',
            xaxis_title='Required Skill',
            yaxis_title='Avg Success Probability',
            barmode='group',
            height=400,
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_skill, use_container_width=True)
    
    # Scatter plot: Success vs Distance
    st.subheader("Success Probability vs Distance")
    
    fig_scatter = px.scatter(
        filtered_df,
        x='Optimized_distance_km',
        y='Predicted_success_prob',
        color='Fallback_level',
        size='Optimized_workload_ratio',
        hover_data=['Dispatch_id', 'Required_skill', 'City'],
        title='Success Probability vs Distance (size = workload)',
        labels={
            'Optimized_distance_km': 'Distance (km)',
            'Predicted_success_prob': 'Success Probability'
        }
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)

# TAB 3: Distance Analysis
with tab3:
    st.subheader("Distance Optimization Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distance change histogram
        fig_dist_change = px.histogram(
            filtered_df,
            x='Distance_change_km',
            nbins=50,
            title='Distance Change Distribution',
            labels={'Distance_change_km': 'Distance Change (km)', 'count': 'Number of Dispatches'},
            color_discrete_sequence=['#e67e22']
        )
        fig_dist_change.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_dist_change, use_container_width=True)
        
        # Distance statistics
        st.markdown("**Distance Statistics:**")
        total_initial = filtered_df['Initial_distance_km'].sum()
        total_optimized = filtered_df['Optimized_distance_km'].sum()
        total_saved = total_initial - total_optimized
        
        st.write(f"- Total Initial Distance: **{total_initial:,.0f} km**")
        st.write(f"- Total Optimized Distance: **{total_optimized:,.0f} km**")
        st.write(f"- Total Distance Saved: **{total_saved:,.0f} km** ({(total_saved/total_initial*100):.1f}%)")
        st.write(f"- Estimated Fuel Savings: **${abs(total_saved * 0.50):,.0f}**")
        st.write(f"- Estimated Time Saved: **{abs(total_saved * 2):,.0f} minutes**")
    
    with col2:
        # Distance by city
        city_distance = filtered_df.groupby('City').agg({
            'Initial_distance_km': 'mean',
            'Optimized_distance_km': 'mean'
        }).reset_index()
        
        fig_city = go.Figure()
        fig_city.add_trace(go.Bar(
            x=city_distance['City'],
            y=city_distance['Initial_distance_km'],
            name='Initial',
            marker_color='salmon'
        ))
        fig_city.add_trace(go.Bar(
            x=city_distance['City'],
            y=city_distance['Optimized_distance_km'],
            name='Optimized',
            marker_color='lightcoral'
        ))
        
        fig_city.update_layout(
            title='Average Distance by City',
            xaxis_title='City',
            yaxis_title='Average Distance (km)',
            barmode='group',
            height=400,
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_city, use_container_width=True)

# TAB 4: Workload Balance
with tab4:
    st.subheader("Technician Workload Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Workload distribution
        fig_workload = go.Figure()
        
        fig_workload.add_trace(go.Histogram(
            x=filtered_df['Initial_workload_ratio'],
            name='Initial',
            opacity=0.7,
            marker_color='lightblue',
            nbinsx=30
        ))
        
        fig_workload.add_trace(go.Histogram(
            x=filtered_df['Optimized_workload_ratio'],
            name='Optimized',
            opacity=0.7,
            marker_color='lightgreen',
            nbinsx=30
        ))
        
        fig_workload.add_vline(x=0.8, line_dash="dash", line_color="orange", 
                               annotation_text="80% capacity")
        fig_workload.add_vline(x=1.0, line_dash="dash", line_color="red", 
                               annotation_text="100% capacity")
        
        fig_workload.update_layout(
            title='Workload Ratio Distribution',
            xaxis_title='Workload Ratio',
            yaxis_title='Number of Assignments',
            barmode='overlay',
            height=400
        )
        
        st.plotly_chart(fig_workload, use_container_width=True)
    
    with col2:
        # Workload statistics
        st.markdown("**Workload Statistics:**")
        
        initial_over_80 = (filtered_df['Initial_workload_ratio'] > 0.8).sum()
        optimized_over_80 = (filtered_df['Optimized_workload_ratio'] > 0.8).sum()
        
        initial_over_100 = (filtered_df['Initial_workload_ratio'] > 1.0).sum()
        optimized_over_100 = (filtered_df['Optimized_workload_ratio'] > 1.0).sum()
        
        st.write(f"**Initial Assignments:**")
        st.write(f"- Over 80% capacity: **{initial_over_80}** ({(initial_over_80/len(filtered_df)*100):.1f}%)")
        st.write(f"- Over 100% capacity: **{initial_over_100}** ({(initial_over_100/len(filtered_df)*100):.1f}%)")
        
        st.write(f"\n**Optimized Assignments:**")
        st.write(f"- Over 80% capacity: **{optimized_over_80}** ({(optimized_over_80/len(filtered_df)*100):.1f}%)")
        st.write(f"- Over 100% capacity: **{optimized_over_100}** ({(optimized_over_100/len(filtered_df)*100):.1f}%)")
        
        # Workload change
        fig_workload_change = px.histogram(
            filtered_df,
            x='Workload_ratio_change',
            nbins=50,
            title='Workload Ratio Change',
            labels={'Workload_ratio_change': 'Workload Change', 'count': 'Count'},
            color_discrete_sequence=['#9b59b6']
        )
        fig_workload_change.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_workload_change, use_container_width=True)

# TAB 5: Individual Dispatches
with tab5:
    st.subheader("Individual Dispatch Details")
    
    # Search by Dispatch ID
    search_id = st.text_input("Search by Dispatch ID", "")
    
    if search_id:
        filtered_df = filtered_df[filtered_df['Dispatch_id'].astype(str).str.contains(search_id)]
    
    # Display mode
    display_mode = st.radio(
        "Display Mode",
        ["Show All Columns", "Show Key Metrics Only"],
        horizontal=True
    )
    
    if display_mode == "Show Key Metrics Only":
        columns_to_show = [
            'Dispatch_id', 'City', 'Required_skill',
            'Assigned_technician_id', 'Optimized_technician_id',
            'Initial_success_prob', 'Predicted_success_prob', 'Success_prob_improvement',
            'Initial_distance_km', 'Optimized_distance_km', 'Distance_change_km',
            'Fallback_level'
        ]
        display_df = filtered_df[columns_to_show]
    else:
        display_df = filtered_df
    
    # Color code improvements
    def highlight_improvements(row):
        if row['Success_prob_improvement'] > 0:
            return ['background-color: #d5f4e6'] * len(row)
        elif row['Success_prob_improvement'] < 0:
            return ['background-color: #fadbd8'] * len(row)
        else:
            return [''] * len(row)
    
    # Display dataframe
    st.dataframe(
        display_df.style.apply(highlight_improvements, axis=1),
        use_container_width=True,
        height=400
    )
    
    # Download filtered data
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name=f"filtered_dispatches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ============================================================
# FALLBACK LEVEL ANALYSIS
# ============================================================
st.markdown("---")
st.header("🎯 Fallback Level Analysis")

col1, col2 = st.columns(2)

with col1:
    # Fallback level distribution
    fallback_counts = filtered_df['Fallback_level'].value_counts()
    
    fig_fallback = px.pie(
        values=fallback_counts.values,
        names=fallback_counts.index,
        title='Fallback Level Distribution',
        hole=0.3
    )
    
    st.plotly_chart(fig_fallback, use_container_width=True)

with col2:
    # Success probability by fallback level
    fallback_success = filtered_df.groupby('Fallback_level')['Predicted_success_prob'].agg(['mean', 'count']).reset_index()
    
    fig_fallback_success = px.bar(
        fallback_success,
        x='Fallback_level',
        y='mean',
        title='Average Success Probability by Fallback Level',
        labels={'mean': 'Avg Success Probability', 'Fallback_level': 'Fallback Level'},
        text='count',
        color='mean',
        color_continuous_scale='RdYlGn'
    )
    
    fig_fallback_success.update_traces(texttemplate='n=%{text}', textposition='outside')
    
    st.plotly_chart(fig_fallback_success, use_container_width=True)

# ============================================================
# SYSTEM INFORMATION
# ============================================================
st.markdown("---")
st.header("ℹ️ System Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Assignment Mode:**")
    # Check if ml_based is in fallback levels
    if 'ml_based' in df['Fallback_level'].unique():
        st.success("🤖 ML-Based Assignment")
        st.write("Evaluates ALL available technicians using ML model")
    else:
        st.info("📋 Legacy Cascading Fallback")

with col2:
    st.markdown("**Optimization Timestamp:**")
    if 'Optimization_timestamp' in df.columns:
        timestamp = df['Optimization_timestamp'].iloc[0]
        st.write(f"🕐 {timestamp}")
    else:
        st.write("N/A")

with col3:
    st.markdown("**Data Summary:**")
    st.write(f"- Total Dispatches: **{len(df)}**")
    st.write(f"- Unique Cities: **{df['City'].nunique()}**")
    st.write(f"- Unique Skills: **{df['Required_skill'].nunique()}**")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #7f8c8d; padding: 20px;'>
        <p>Smart Dispatch Optimization Dashboard v1.0</p>
        <p>Powered by ML-Based Assignment System | Built with Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)

