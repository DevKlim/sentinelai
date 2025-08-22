# Resume Highlights

This document outlines key accomplishments and skills demonstrated through the projects in this repository.

## Potential Roles

*   **AI/ML Engineer:** Focus on the design, development, and deployment of machine learning models, particularly in the areas of Natural Language Processing (NLP) and speech recognition.
*   **Data Scientist:** Analyze complex datasets, extract meaningful insights, and build predictive models to solve business problems.
*   **Software Engineer (AI/ML Focus):** Develop robust and scalable software systems that integrate and support AI/ML models.
*   **DevOps Engineer:** Automate and streamline the development, deployment, and operations of software systems, with a focus on MLOps.
*   **Full-Stack Developer:** Build and maintain both the front-end and back-end components of web applications, with a focus on data-driven applications.
*   **Technical Lead/Architect:** Lead the design and development of complex software systems, providing technical guidance and mentorship to a team of engineers.

## Leadership & Mentorship

*   **Guided Intern Team to Success:** Led and mentored a team of interns in the development of a critical component of the emergency response pipeline: a Whisper-based voice-to-text model for 911 calls. This involved providing technical guidance, project management, and fostering a collaborative learning environment. The successful completion of this project under my leadership demonstrates strong mentorship and team leadership skills.

## AI/ML Engineering

*   **Fine-tuned and Deployed LLMs for Geocoding:** Developed and deployed a fine-tuned Large Language Model for high-accuracy geocoding of incident data. This involved data processing, model fine-tuning, and deployment as a containerized service.
*   **Real-Time 911 Call Transcription:** Architected and trained a voice-to-text model using Whisper for real-time transcription of 911 calls. This model is a core component of the emergency response pipeline.
*   **Intelligent Incident Categorization:** Designed and built an AI-powered system for categorizing and correlating emergency incidents. This system uses a Large Language Model to analyze incoming incident reports and determine if they are new incidents or updates to existing ones, significantly improving the efficiency of emergency response.
*   **Duplicate Incident Detection:** Built a system to identify and respond to duplicate emergency incidents, optimizing resource allocation for emergency services.
*   **Real-Time Alert System:** Developed a system for generating real-time alerts from incoming data streams, enabling faster response times.
*   **EIDO Standardization:** Worked extensively with the Emergency Incident Data Object (EIDO) standard, developing tools for parsing and generating EIDO-compliant data.
*   **RAG Implementation:** Implemented a Retrieval-Augmented Generation (RAG) system for contextualizing and enriching incident data, improving the accuracy of generated EIDO reports.

## Software Engineering & DevOps

*   **Multi-Agent System Architecture:** Designed and implemented a sophisticated multi-agent system for a complete emergency response data pipeline. This system consists of multiple, independent agents that communicate with each other through APIs.
*   **Microservices Orchestration:** Orchestrated a complex system of microservices using Docker and Docker Compose. A central Nginx server acts as a reverse proxy and API gateway, routing traffic to the appropriate services.
*   **Full-Stack Development:** Developed both front-end and back-end components of the system, including a web dashboard using Streamlit and a landing page using Next.js and React. The backend is powered by FastAPI and communicates with a PostgreSQL database.
*   **API Development:** Built and deployed numerous RESTful APIs using FastAPI for services within the ecosystem, facilitating communication and data exchange between components.
*   **CI/CD and Automation:** Implemented automated scripts for building, testing, and deploying services, streamlining the development lifecycle.
*   **Cloud Deployment & Management:** Deployed and managed services on Fly.io, including configuring environments, monitoring application health, and scaling resources.

## Database Management

*   **PostgreSQL Administration:** Managed a PostgreSQL database for storing incident data, including schema design, data modeling, and performance tuning.
*   **Supabase Integration:** Utilized Supabase for database hosting, authentication, and real-time data synchronization, simplifying the development of data-intensive applications.

## Technical Deep Dive

### AI/ML

*   **Model:** Fine-tuned OpenAI Whisper Base (74M parameters) for specialized emergency call transcription.
*   **Accuracy:** Achieved a Word Error Rate (WER) of 1.2201 on a dataset of 707 full-length emergency 911 calls.
*   **Performance:** Optimized the model for real-time performance, achieving a 0.05x real-time factor (processing a 10-second audio chunk in ~0.3 seconds).
*   **Customization:** Enhanced the model with a custom loss function that applies a 2.0x weight to over 40 emergency-specific keywords, significantly improving the detection of critical information.
*   **Audio Processing:** Implemented a robust audio processing pipeline including noise reduction (spectral subtraction), vocal enhancement, Voice Activity Detection (VAD), and support for multiple audio formats (WAV, MP3, M4A, FLAC).
*   **Training Pipeline:** Built a comprehensive training pipeline featuring data augmentation (pitch shifting, speed changes, noise injection) and detailed evaluation metrics (WER, CER).
*   **Distribution:** Engineered a smart model distribution system using HuggingFace Hub, eliminating the need for Git LFS and enabling automated downloads with failover options.

### Software Architecture & DevOps

*   **Microservices:** Designed and implemented a multi-container architecture using Docker and Docker Compose to orchestrate a suite of Python-based microservices.
*   **Services:**
    *   **`sentinelai`:** A central orchestrator and API gateway that routes requests to the appropriate agents.
    *   **`eido-agent`:** An agent responsible for ingesting raw data, generating structured EIDO reports using a RAG pipeline, and managing EIDO templates.
    *   **`idx-agent`:** An agent that intelligently categorizes and correlates incidents using an LLM, identifying duplicates and linking related events.
    *   **`eido_db`:** A PostgreSQL database for storing incident data.
    *   **`dashboard`:** A Streamlit-based web dashboard for data visualization and monitoring.
    *   **`landing`:** A modern, investor-ready landing page.
*   **API Gateway:** Utilized Nginx as a reverse proxy and API gateway to route traffic to the appropriate services.
*   **Database:** Employed a PostgreSQL database with a healthcheck to ensure service availability.
*   **Environment Management:** Utilized `.env` files for secure management of environment variables and API keys.
*   **Scalability:** The microservices architecture is designed for scalability and maintainability, allowing for individual components to be updated and scaled independently.

### Web Development

*   **Frontend:** Developed interactive web interfaces using Streamlit and a Next.js landing page, providing a user-friendly way to interact with the AI models and view data.
*   **Backend:** Built RESTful APIs using FastAPI to expose the functionality of the AI models and data services.
*   **Real-Time Features:** Implemented real-time transcription with live microphone input and a demonstration mode for showcasing the system's capabilities.
*   **UI/UX:** Designed a professional and intuitive web interface with multiple tabs for different functionalities, including file uploads, live recording, and model information.

## Technology Stack

### AI & Machine Learning

*   **PyTorch:** Core deep learning framework for model training and inference.
*   **Hugging Face Transformers:** Utilized for accessing and fine-tuning the Whisper model.
*   **Hugging Face PEFT (Parameter-Efficient Fine-Tuning):** Employed for efficient fine-tuning of the language model.
*   **Accelerate:** A library from Hugging Face to simplify distributed training and inference.
*   **BitsAndBytes:** Used for 8-bit optimizers and quantization to reduce memory footprint.
*   **Loralib:** Implemented LoRA (Low-Rank Adaptation) for efficient fine-tuning.
*   **Datasets:** Used for loading and processing the training data.
*   **Librosa & SciPy:** Core libraries for audio processing and analysis.
*   **Scikit-learn:** Used for machine learning utilities and evaluation metrics.
*   **WandB (Weights & Biases):** Integrated for experiment tracking, visualization, and model logging.

### Backend & API

*   **FastAPI:** A modern, high-performance web framework for building RESTful APIs.
*   **Uvicorn:** An ASGI server for running FastAPI applications.
*   **Pydantic:** Used for data validation and settings management.
*   **PostgreSQL:** A powerful, open-source object-relational database system.
*   **Supabase:** A backend-as-a-service platform for database hosting, authentication, and real-time data synchronization.

### Frontend & Data Visualization

*   **Streamlit:** A fast and easy way to build and share data apps.
*   **Gradio:** Used to create simple web interfaces for machine learning models.
*   **Matplotlib & Seaborn:** Core libraries for creating static, animated, and interactive visualizations.
*   **Next.js & React:** A popular framework for building server-side rendered and static web applications.
*   **Tailwind CSS & PostCSS:** A utility-first CSS framework and a tool for transforming CSS with JavaScript plugins.

### Audio Processing

*   **Pydub:** A simple and high-level interface for audio manipulation.
*   **webrtcvad-wheels:** A library for voice activity detection.
*   **Sounddevice:** Used for recording and playing audio.
*   **Spleeter:** A library for audio source separation.
*   **ultimate-vocal-remover:** A tool for vocal removal from audio tracks.