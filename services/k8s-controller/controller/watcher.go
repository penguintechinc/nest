package controller

import (
	"context"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
)

// Watcher watches Kubernetes resources for changes
type Watcher struct {
	clientset       *kubernetes.Clientset
	namespacePrefix string
	eventChannel    chan ResourceEvent
	log             *logrus.Entry
}

// ResourceEvent represents a change to a Kubernetes resource
type ResourceEvent struct {
	Type      watch.EventType
	Namespace string
	Name      string
	Resource  interface{}
}

// NewWatcher creates a new Kubernetes resource watcher
func NewWatcher(clientset *kubernetes.Clientset, namespacePrefix string) *Watcher {
	return &Watcher{
		clientset:       clientset,
		namespacePrefix: namespacePrefix,
		eventChannel:    make(chan ResourceEvent, 100),
		log:             logrus.WithField("component", "watcher"),
	}
}

// Start begins watching Kubernetes resources
func (w *Watcher) Start(ctx context.Context) error {
	w.log.Info("Starting Kubernetes resource watcher")

	// Get list of team namespaces
	namespaces, err := w.getTeamNamespaces(ctx)
	if err != nil {
		return fmt.Errorf("failed to get namespaces: %w", err)
	}

	w.log.WithField("count", len(namespaces)).Info("Found team namespaces")

	// Start watching StatefulSets in each namespace
	for _, ns := range namespaces {
		go w.watchStatefulSets(ctx, ns)
		go w.watchPods(ctx, ns)
	}

	return nil
}

// GetEventChannel returns the channel for resource events
func (w *Watcher) GetEventChannel() <-chan ResourceEvent {
	return w.eventChannel
}

// getTeamNamespaces returns all namespaces with the team prefix
func (w *Watcher) getTeamNamespaces(ctx context.Context) ([]string, error) {
	namespaces, err := w.clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var teamNamespaces []string
	for _, ns := range namespaces.Items {
		if len(w.namespacePrefix) == 0 || hasPrefix(ns.Name, w.namespacePrefix) {
			teamNamespaces = append(teamNamespaces, ns.Name)
		}
	}

	return teamNamespaces, nil
}

// watchStatefulSets watches StatefulSet resources in a namespace
func (w *Watcher) watchStatefulSets(ctx context.Context, namespace string) {
	log := w.log.WithFields(logrus.Fields{
		"namespace": namespace,
		"resource":  "StatefulSet",
	})

	for {
		select {
		case <-ctx.Done():
			log.Info("Stopping StatefulSet watcher")
			return
		default:
		}

		watcher, err := w.clientset.AppsV1().StatefulSets(namespace).Watch(ctx, metav1.ListOptions{})
		if err != nil {
			log.WithError(err).Error("Failed to create StatefulSet watcher")
			time.Sleep(5 * time.Second)
			continue
		}

		log.Info("Started watching StatefulSets")

		for event := range watcher.ResultChan() {
			if event.Object == nil {
				continue
			}

			sts, ok := event.Object.(*appsv1.StatefulSet)
			if !ok {
				continue
			}

			w.eventChannel <- ResourceEvent{
				Type:      event.Type,
				Namespace: namespace,
				Name:      sts.Name,
				Resource:  sts,
			}

			log.WithFields(logrus.Fields{
				"type": event.Type,
				"name": sts.Name,
			}).Debug("StatefulSet event received")
		}

		log.Warn("StatefulSet watcher closed, restarting...")
		time.Sleep(5 * time.Second)
	}
}

// watchPods watches Pod resources in a namespace
func (w *Watcher) watchPods(ctx context.Context, namespace string) {
	log := w.log.WithFields(logrus.Fields{
		"namespace": namespace,
		"resource":  "Pod",
	})

	for {
		select {
		case <-ctx.Done():
			log.Info("Stopping Pod watcher")
			return
		default:
		}

		watcher, err := w.clientset.CoreV1().Pods(namespace).Watch(ctx, metav1.ListOptions{})
		if err != nil {
			log.WithError(err).Error("Failed to create Pod watcher")
			time.Sleep(5 * time.Second)
			continue
		}

		log.Info("Started watching Pods")

		for event := range watcher.ResultChan() {
			if event.Object == nil {
				continue
			}

			pod, ok := event.Object.(*corev1.Pod)
			if !ok {
				continue
			}

			w.eventChannel <- ResourceEvent{
				Type:      event.Type,
				Namespace: namespace,
				Name:      pod.Name,
				Resource:  pod,
			}

			log.WithFields(logrus.Fields{
				"type":  event.Type,
				"name":  pod.Name,
				"phase": pod.Status.Phase,
			}).Debug("Pod event received")
		}

		log.Warn("Pod watcher closed, restarting...")
		time.Sleep(5 * time.Second)
	}
}

// hasPrefix checks if a string has the given prefix
func hasPrefix(s, prefix string) bool {
	if len(prefix) > len(s) {
		return false
	}
	return s[:len(prefix)] == prefix
}
