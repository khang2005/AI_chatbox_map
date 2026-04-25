FROM node:20 as builder

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . ./

ARG REACT_APP_GOOGLE_MAPS_API_KEY
ARG REACT_APP_BACKEND_URL

ENV REACT_APP_GOOGLE_MAPS_API_KEY=$REACT_APP_GOOGLE_MAPS_API_KEY
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]