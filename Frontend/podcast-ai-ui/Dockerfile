# Use an official Node.js runtime as a base image
FROM node:18-alpine AS builder

# Set working directory inside the container
WORKDIR /app

# Copy only package.json and package-lock.json for better caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application files
COPY . .

# Set environment to production
ENV NODE_ENV=production

# Build the Next.js app (this will compile TypeScript files)
RUN npm run build

# --------------------
# Production Stage
# --------------------
FROM node:18-alpine AS runner

WORKDIR /app

# Copy only the necessary files from the builder stage
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

# Expose the Next.js port
EXPOSE 3000

# Start the Next.js app
CMD ["npm", "run", "start"]
