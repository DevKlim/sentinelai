# Sentinel EIDO IDX Project

This repository contains three interconnected projects for emergency incident management and response:

## Projects Overview

### 1. EIDO Agent (`eido-agent/`)
A comprehensive emergency incident detection and response system that processes EIDO (Emergency Incident Data Object) reports.

**Key Features:**
- EIDO report parsing and processing
- Geocoding and location services
- Alert matching and classification
- LLM-powered incident analysis
- Web-based dashboard interface
- RESTful API endpoints

**Technologies:**
- Python (FastAPI, Streamlit)
- Docker containerization
- Vector embeddings for similarity search
- Geocoding services

### 2. IDX Agent (`idx-agent/`)
An intelligent document indexing and search system for emergency response data.

**Key Features:**
- Document indexing and search
- EIDO service integration
- Streamlit-based user interface
- RESTful API for document operations

**Technologies:**
- Python (FastAPI, Streamlit)
- Document processing and indexing
- Search algorithms

### 3. Sentinel AI (`sentinelai/`)
A unified dashboard and orchestration platform that integrates both EIDO and IDX agents.

**Key Features:**
- Unified web interface
- Multi-agent orchestration
- Dashboard for monitoring and control
- Authentication and user management
- Nginx reverse proxy configuration

**Technologies:**
- Python (Streamlit, FastAPI)
- Docker Compose for orchestration
- Nginx for load balancing
- Multi-container architecture

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Git

### Running the Complete System

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vaishnav90/sentinel-eido-idx.git
   cd sentinel-eido-idx
   ```

2. **Start the Sentinel AI dashboard:**
   ```bash
   cd sentinelai
   docker-compose up -d
   ```

3. **Access the dashboard:**
   - Main dashboard: http://localhost:8501
   - EIDO Agent: http://localhost:8502
   - IDX Agent: http://localhost:8503

### Individual Project Setup

#### EIDO Agent
```bash
cd eido-agent
pip install -r requirements.txt
python -m streamlit run ui/app.py
```

#### IDX Agent
```bash
cd idx-agent
pip install -r requirements.txt
python -m streamlit run ui/app.py
```

#### Sentinel AI
```bash
cd sentinelai
pip install -r requirements.txt
python main.py
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sentinel AI   │    │   EIDO Agent    │    │   IDX Agent     │
│   (Dashboard)   │◄──►│   (Incident     │    │   (Document     │
│                 │    │    Processing)  │    │    Indexing)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Shared Data   │
                    │   & Services    │
                    └─────────────────┘
```

## API Documentation

- **EIDO Agent API**: Available at `/docs` when running the EIDO agent
- **IDX Agent API**: Available at `/docs` when running the IDX agent
- **Sentinel AI API**: Integrated APIs accessible through the main dashboard

## Development

### Project Structure
```
sentinel-eido-idx/
├── eido-agent/          # Emergency incident processing
├── idx-agent/           # Document indexing and search
├── sentinelai/          # Unified dashboard
└── README.md           # This file
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub or contact the development team. 