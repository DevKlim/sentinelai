# sdsc-orchestrator/landing/Dockerfile
# Stage 1: Build the Next.js application
FROM node:18-alpine AS builder

# Set the working directory
WORKDIR /app

# Copy package files and install dependencies
# This leverages Docker's layer caching
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy the rest of the application source code
COPY . .

# Build the application for production (this creates the 'out' folder)
# The output: "export" in next.config.mjs ensures this command generates a static site in the 'out' directory.
RUN npm run build

# Stage 2: Production image with Nginx
FROM nginx:alpine

# Copy the static output from the builder stage to the Nginx html directory
COPY --from=builder /app/out /usr/share/nginx/html

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 and start Nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]