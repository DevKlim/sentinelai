# Stage 1: Install dependencies
# This stage installs dependencies and resolves conflicts.
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# Use --legacy-peer-deps to resolve conflicts. This might update package-lock.json.
RUN npm install --legacy-peer-deps

# Stage 2: Build the application
# This stage builds the Next.js app using the installed dependencies.
FROM node:18-alpine AS builder
WORKDIR /app
# First, copy the entire source code.
COPY . .
# Then, copy the installed node_modules from the 'deps' stage.
COPY --from=deps /app/node_modules ./node_modules
# Crucially, overwrite the original package-lock.json with the (potentially updated)
# one from the 'deps' stage to ensure consistency.
COPY --from=deps /app/package-lock.json ./
# Now, run the build.
RUN npm run build

# Stage 3: Production image
# This is the final, small, and optimized image.
FROM nginx:alpine
# Copy the static output from the builder stage.
COPY --from=builder /app/out /usr/share/nginx/html
# Copy the custom Nginx configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]