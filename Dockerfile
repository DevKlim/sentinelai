# Stage 1: Serve the application with Nginx
FROM nginx:1.25-alpine

# Copy the website files
COPY ./landing /usr/share/nginx/html
COPY ./dashboard /usr/share/nginx/html/dashboard

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]