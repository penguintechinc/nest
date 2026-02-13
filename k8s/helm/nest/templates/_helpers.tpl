{{/*
Expand the name of the chart.
*/}}
{{- define "nest.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "nest.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "nest.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nest.labels" -}}
helm.sh/chart: {{ include "nest.chart" . }}
{{ include "nest.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nest.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nest.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "nest.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "nest.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Component labels for postgres
*/}}
{{- define "nest.postgres.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: postgres
{{- end }}

{{/*
Component labels for redis
*/}}
{{- define "nest.redis.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: redis
{{- end }}

{{/*
Component labels for api
*/}}
{{- define "nest.api.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Component labels for manager
*/}}
{{- define "nest.manager.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: manager
{{- end }}

{{/*
Component labels for web
*/}}
{{- define "nest.web.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: web
{{- end }}

{{/*
Component labels for prometheus
*/}}
{{- define "nest.prometheus.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: prometheus
{{- end }}

{{/*
Component labels for grafana
*/}}
{{- define "nest.grafana.labels" -}}
{{ include "nest.labels" . }}
app.kubernetes.io/component: grafana
{{- end }}

{{/*
Image name helper
*/}}
{{- define "nest.image" -}}
{{- $registry := .registry -}}
{{- $repository := .repository -}}
{{- $tag := .tag -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}
