FROM node:22-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Next.js bakes rewrites (the /api and /auth proxy targets) into the build,
# so the backend URL must be known at build time, not just at runtime.
ARG BACKEND_URL=http://backend:8002
ENV BACKEND_URL=${BACKEND_URL} \
    AUTH_URL=${BACKEND_URL} \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Build the Next.js project
RUN npm run build

# Expose Next.js default port
EXPOSE 3000
ENV PORT=3000

# Start Next.js server
CMD ["npm", "start"]
