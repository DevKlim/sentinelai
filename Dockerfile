# Stage 1: Serve the application with Nginx
FROM nginx:1.25-alpine

# Copy the website files
COPY ./website /usr/share/nginx/html

# Copy the nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80