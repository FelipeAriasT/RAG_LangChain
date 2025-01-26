
FROM downloads.unstructured.io/unstructured-io/unstructured:latest

USER root
RUN apk update && apk add posix-libc-utils 

# (Opcional) Cambia de nuevo el usuario al final si lo necesitas
# USER notebook-user