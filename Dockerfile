# Multi-stage build for React app
FROM node:18-alpine as build

WORKDIR /app
COPY app/package*.json ./
RUN npm ci --only=production

COPY app/ .
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built React app
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]