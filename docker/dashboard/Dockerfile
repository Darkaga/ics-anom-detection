FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    streamlit==1.28.0 \
    plotly==5.17.0 \
    pandas==2.1.3 \
    requests==2.31.0 \
    altair==5.1.2

# Copy dashboard code
COPY dashboard.py /app/
COPY .streamlit/ /app/.streamlit/

# Expose Streamlit port
EXPOSE 8501

# Run dashboard
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
