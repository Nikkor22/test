FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy app
COPY . .

# Expose port
EXPOSE 5173

# Run dev server
CMD ["npm", "run", "dev", "--", "--host"]
