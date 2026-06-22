FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Set environment to production and disable Next.js telemetry
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Build the Next.js project
RUN npm run build

# Expose Next.js default port
EXPOSE 3000
ENV PORT=3000

# Start Next.js server
CMD ["npm", "start"]
