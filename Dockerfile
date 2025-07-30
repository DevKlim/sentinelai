
FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY landing/dist /usr/share/nginx/html/landing

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
