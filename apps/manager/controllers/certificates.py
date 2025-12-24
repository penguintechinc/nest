"""
Certificates Controller

Handles certificate authority (CA) and certificate lifecycle management including:
- CA creation, import, and deletion
- Certificate generation and renewal
- TLS integration with Kubernetes resources
- RBAC-enforced access control
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import base64

from lib.ca_manager import CAManager, CAManagerException
from lib.k8s_client import KubernetesClient, KubernetesClientException


logger = logging.getLogger(__name__)


class CertificateAccessDenied(Exception):
    """Exception raised when user lacks required permissions"""
    pass


class CertificateNotFound(Exception):
    """Exception raised when certificate or CA not found"""
    pass


class CertificatesController:
    """
    Controller for managing Certificate Authorities and Certificates.

    Enforces RBAC:
    - CA operations: GlobalAdmin only
    - Certificate operations: TeamAdmin or GlobalAdmin
    - View operations: Team members
    """

    def __init__(self, db, k8s_client: Optional[KubernetesClient] = None):
        """
        Initialize certificates controller.

        Args:
            db: PyDAL DAL instance
            k8s_client: Optional Kubernetes client for secret management
        """
        self.db = db
        self.k8s_client = k8s_client
        self.ca_manager = CAManager()

    # ====== RBAC Helper Methods ======

    def _is_global_admin(self, user_id: int) -> bool:
        """
        Check if user is a global administrator.

        Args:
            user_id: ID of user to check

        Returns:
            True if user is global admin, False otherwise
        """
        # Get user's global team membership
        membership = self.db(
            (self.db.team_memberships.user_id == user_id) &
            (self.db.teams.is_global == True) &
            (self.db.team_memberships.team_id == self.db.teams.id)
        ).select(self.db.team_memberships.role).first()

        return membership and membership.role == 'admin'

    def _get_user_team_role(self, user_id: int, team_id: int) -> Optional[str]:
        """
        Get user's role in a specific team.

        Args:
            user_id: ID of user
            team_id: ID of team

        Returns:
            User's role (admin, member, viewer) or None if not member
        """
        membership = self.db(
            (self.db.team_memberships.user_id == user_id) &
            (self.db.team_memberships.team_id == team_id)
        ).select(self.db.team_memberships.role).first()

        return membership.role if membership else None

    def _check_ca_access(self, user_id: int) -> None:
        """
        Check if user can manage CAs (GlobalAdmin only).

        Args:
            user_id: ID of user to check

        Raises:
            CertificateAccessDenied: If user is not global admin
        """
        if not self._is_global_admin(user_id):
            raise CertificateAccessDenied("Only global administrators can manage CAs")

    def _check_certificate_access(self, user_id: int, team_id: int) -> None:
        """
        Check if user can manage certificates in team (TeamAdmin or GlobalAdmin).

        Args:
            user_id: ID of user to check
            team_id: ID of team

        Raises:
            CertificateAccessDenied: If user lacks required permission
        """
        if self._is_global_admin(user_id):
            return  # Global admin can do everything

        role = self._get_user_team_role(user_id, team_id)
        if role != 'admin':
            raise CertificateAccessDenied(
                "User must be team admin or global admin to manage certificates"
            )

    def _check_certificate_view(self, user_id: int, team_id: int) -> None:
        """
        Check if user can view certificates in team (any team member).

        Args:
            user_id: ID of user to check
            team_id: ID of team

        Raises:
            CertificateAccessDenied: If user is not team member
        """
        if self._is_global_admin(user_id):
            return  # Global admin can view everything

        role = self._get_user_team_role(user_id, team_id)
        if not role:
            raise CertificateAccessDenied("User is not member of this team")

    def _create_audit_log(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        team_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create an audit log entry.

        Args:
            user_id: User who performed action
            action: Action name
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            team_id: Team context
            details: Additional details
        """
        try:
            self.db.audit_logs.insert(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                team_id=team_id,
                details=details
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

    # ====== CA Management Methods ======

    def create_ca(
        self,
        name: str,
        ca_type: str,
        common_name: str,
        organization: str,
        user_id: int,
        organization_unit: Optional[str] = None,
        country: str = "US",
        state: str = "CA",
        locality: str = "San Francisco",
        validity_days: int = 3650
    ) -> Dict[str, Any]:
        """
        Create a new internal Certificate Authority.

        Args:
            name: CA name for identification
            ca_type: Type of CA (root or intermediate)
            common_name: CN for CA certificate
            organization: Organization name
            user_id: User creating CA
            organization_unit: Optional organization unit
            country: Country code (default: US)
            state: State/province (default: CA)
            locality: Locality (default: San Francisco)
            validity_days: Certificate validity in days (default: 3650 = 10 years)

        Returns:
            Dictionary with CA details including id, certificate, and metadata

        Raises:
            CertificateAccessDenied: If user is not global admin
            CAManagerException: If CA generation fails
        """
        self._check_ca_access(user_id)

        try:
            # Generate CA certificate
            if ca_type == 'root':
                cert_data = self.ca_manager.generate_root_ca(
                    common_name=common_name,
                    organization=organization,
                    organization_unit=organization_unit,
                    country=country,
                    state=state,
                    locality=locality,
                    validity_days=validity_days
                )
            elif ca_type == 'intermediate':
                cert_data = self.ca_manager.generate_intermediate_ca(
                    common_name=common_name,
                    organization=organization,
                    organization_unit=organization_unit,
                    country=country,
                    state=state,
                    locality=locality,
                    validity_days=validity_days
                )
            else:
                raise ValueError(f"Invalid CA type: {ca_type}")

            # Extract certificate details
            cert_obj = self.ca_manager.parse_certificate(cert_data['certificate'])

            # Store in database
            ca_id = self.db.certificate_authorities.insert(
                name=name,
                type=ca_type,
                certificate=cert_data['certificate'],
                private_key=cert_data['private_key'],
                subject=self.ca_manager.get_certificate_subject(cert_obj),
                issuer=self.ca_manager.get_certificate_issuer(cert_obj),
                valid_from=self.ca_manager.get_certificate_not_before(cert_obj),
                valid_until=self.ca_manager.get_certificate_not_after(cert_obj),
                serial_number=str(self.ca_manager.get_certificate_serial_number(cert_obj)),
                is_nest_managed=True,
                created_by=user_id
            )
            self.db.commit()

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action='ca_created',
                resource_type='certificate_authority',
                resource_id=ca_id,
                details={
                    'name': name,
                    'type': ca_type,
                    'common_name': common_name
                }
            )

            logger.info(f"Created {ca_type} CA '{name}' with ID {ca_id}")

            return {
                'id': ca_id,
                'name': name,
                'type': ca_type,
                'subject': self.ca_manager.get_certificate_subject(cert_obj),
                'issuer': self.ca_manager.get_certificate_issuer(cert_obj),
                'valid_from': self.ca_manager.get_certificate_not_before(cert_obj),
                'valid_until': self.ca_manager.get_certificate_not_after(cert_obj),
                'serial_number': str(self.ca_manager.get_certificate_serial_number(cert_obj))
            }

        except Exception as e:
            logger.error(f"Failed to create CA: {e}")
            raise

    def import_ca(
        self,
        name: str,
        ca_type: str,
        certificate_pem: str,
        private_key_pem: Optional[str],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Import an existing Certificate Authority.

        Args:
            name: CA name for identification
            ca_type: Type of CA (root, intermediate, or self_signed)
            certificate_pem: PEM-encoded certificate
            private_key_pem: PEM-encoded private key (optional for CA-only import)
            user_id: User importing CA

        Returns:
            Dictionary with CA details including id

        Raises:
            CertificateAccessDenied: If user is not global admin
            ValueError: If certificate format is invalid
        """
        self._check_ca_access(user_id)

        try:
            # Parse and validate certificate
            cert_obj = self.ca_manager.parse_certificate(certificate_pem)

            # Store in database
            ca_id = self.db.certificate_authorities.insert(
                name=name,
                type=ca_type,
                certificate=certificate_pem,
                private_key=private_key_pem,
                subject=self.ca_manager.get_certificate_subject(cert_obj),
                issuer=self.ca_manager.get_certificate_issuer(cert_obj),
                valid_from=self.ca_manager.get_certificate_not_before(cert_obj),
                valid_until=self.ca_manager.get_certificate_not_after(cert_obj),
                serial_number=str(self.ca_manager.get_certificate_serial_number(cert_obj)),
                is_nest_managed=False,
                created_by=user_id
            )
            self.db.commit()

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action='ca_imported',
                resource_type='certificate_authority',
                resource_id=ca_id,
                details={'name': name, 'type': ca_type}
            )

            logger.info(f"Imported {ca_type} CA '{name}' with ID {ca_id}")

            return {
                'id': ca_id,
                'name': name,
                'type': ca_type,
                'subject': self.ca_manager.get_certificate_subject(cert_obj),
                'issuer': self.ca_manager.get_certificate_issuer(cert_obj),
                'valid_from': self.ca_manager.get_certificate_not_before(cert_obj),
                'valid_until': self.ca_manager.get_certificate_not_after(cert_obj),
                'serial_number': str(self.ca_manager.get_certificate_serial_number(cert_obj))
            }

        except Exception as e:
            logger.error(f"Failed to import CA: {e}")
            raise

    def list_cas(self, user_id: int) -> List[Dict[str, Any]]:
        """
        List all Certificate Authorities (GlobalAdmin only).

        Args:
            user_id: User requesting list

        Returns:
            List of CA dictionaries

        Raises:
            CertificateAccessDenied: If user is not global admin
        """
        self._check_ca_access(user_id)

        cas = self.db(self.db.certificate_authorities.deleted_at == None).select()

        return [
            {
                'id': ca.id,
                'name': ca.name,
                'type': ca.type,
                'subject': ca.subject,
                'issuer': ca.issuer,
                'valid_from': ca.valid_from,
                'valid_until': ca.valid_until,
                'is_nest_managed': ca.is_nest_managed,
                'created_at': ca.created_at
            }
            for ca in cas
        ]

    def get_ca(self, ca_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get Certificate Authority details (GlobalAdmin only).

        Args:
            ca_id: ID of CA to retrieve
            user_id: User requesting CA

        Returns:
            CA dictionary with full details

        Raises:
            CertificateAccessDenied: If user is not global admin
            CertificateNotFound: If CA not found
        """
        self._check_ca_access(user_id)

        ca = self.db.certificate_authorities[ca_id]
        if not ca or ca.deleted_at:
            raise CertificateNotFound(f"CA {ca_id} not found")

        return {
            'id': ca.id,
            'name': ca.name,
            'type': ca.type,
            'subject': ca.subject,
            'issuer': ca.issuer,
            'valid_from': ca.valid_from,
            'valid_until': ca.valid_until,
            'is_nest_managed': ca.is_nest_managed,
            'created_by': ca.created_by,
            'created_at': ca.created_at,
            'updated_at': ca.updated_at,
            'certificate': ca.certificate
        }

    def delete_ca(self, ca_id: int, user_id: int) -> None:
        """
        Delete a Certificate Authority (soft delete).

        Prevents deletion if any certificates depend on this CA.

        Args:
            ca_id: ID of CA to delete
            user_id: User deleting CA

        Raises:
            CertificateAccessDenied: If user is not global admin
            CertificateNotFound: If CA not found
            ValueError: If CA has dependent certificates
        """
        self._check_ca_access(user_id)

        ca = self.db.certificate_authorities[ca_id]
        if not ca or ca.deleted_at:
            raise CertificateNotFound(f"CA {ca_id} not found")

        # Check for dependent certificates
        dependent_certs = self.db(
            (self.db.certificates.ca_id == ca_id) &
            (self.db.certificates.deleted_at == None)
        ).count()

        if dependent_certs > 0:
            raise ValueError(
                f"Cannot delete CA: {dependent_certs} certificate(s) depend on it"
            )

        # Soft delete
        ca.update_record(deleted_at=datetime.now())
        self.db.commit()

        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action='ca_deleted',
            resource_type='certificate_authority',
            resource_id=ca_id,
            details={'name': ca.name}
        )

        logger.info(f"Deleted CA {ca_id}")

    def get_ca_public_key(self, ca_id: int) -> str:
        """
        Get public key from Certificate Authority for distribution.

        Args:
            ca_id: ID of CA

        Returns:
            PEM-encoded public key

        Raises:
            CertificateNotFound: If CA not found
        """
        ca = self.db.certificate_authorities[ca_id]
        if not ca or ca.deleted_at:
            raise CertificateNotFound(f"CA {ca_id} not found")

        # Extract public key from certificate
        public_key = self.ca_manager.extract_public_key_from_cert(ca.certificate)
        return public_key

    # ====== Certificate Management Methods ======

    def generate_certificate(
        self,
        resource_id: int,
        ca_id: int,
        common_name: str,
        auto_renew: bool = True,
        renewal_threshold_days: int = 30,
        validity_days: int = 365,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a certificate for a resource.

        Builds SAN list from resource metadata and creates Kubernetes Secret if applicable.

        Args:
            resource_id: ID of resource to certificate
            ca_id: ID of CA to sign certificate
            common_name: Certificate common name
            auto_renew: Enable automatic renewal (default: True)
            renewal_threshold_days: Days before expiry to trigger renewal (default: 30)
            validity_days: Certificate validity in days (default: 365)
            user_id: User generating certificate

        Returns:
            Dictionary with certificate details including id

        Raises:
            CertificateNotFound: If resource or CA not found
            CertificateAccessDenied: If user lacks permission
            Exception: If certificate generation fails
        """
        # Load resource
        resource = self.db.resources[resource_id]
        if not resource or resource.deleted_at:
            raise CertificateNotFound(f"Resource {resource_id} not found")

        # Check access if user_id provided
        if user_id:
            self._check_certificate_access(user_id, resource.team_id)

        # Load CA
        ca = self.db.certificate_authorities[ca_id]
        if not ca or ca.deleted_at:
            raise CertificateNotFound(f"CA {ca_id} not found")

        try:
            # Build SAN list
            san_dns = [resource.name]
            san_ips = []

            # Add Kubernetes DNS SAN if applicable
            if resource.k8s_namespace and resource.k8s_resource_name:
                k8s_fqdn = f"{resource.k8s_resource_name}.{resource.k8s_namespace}.svc.cluster.local"
                san_dns.append(k8s_fqdn)

                # Try to get LoadBalancer IP if Kubernetes client available
                if self.k8s_client:
                    try:
                        service = self.k8s_client.get_service(
                            resource.k8s_namespace,
                            resource.k8s_resource_name
                        )
                        # Extract LoadBalancer IP if available
                        if service.status and service.status.load_balancer and \
                           service.status.load_balancer.ingress:
                            for ingress in service.status.load_balancer.ingress:
                                if ingress.ip:
                                    san_ips.append(ingress.ip)
                    except Exception as e:
                        logger.warning(f"Failed to get K8s service IP: {e}")

            # Generate certificate
            cert_data = self.ca_manager.generate_certificate(
                ca_certificate_pem=ca.certificate,
                ca_private_key_pem=ca.private_key,
                common_name=common_name,
                san_dns=san_dns,
                san_ips=san_ips,
                validity_days=validity_days
            )

            # Parse certificate for metadata
            cert_obj = self.ca_manager.parse_certificate(cert_data['certificate'])

            # Store in database
            cert_id = self.db.certificates.insert(
                resource_id=resource_id,
                ca_id=ca_id,
                certificate=cert_data['certificate'],
                private_key=cert_data['private_key'],
                common_name=common_name,
                san_dns=san_dns,
                san_ips=san_ips,
                valid_from=self.ca_manager.get_certificate_not_before(cert_obj),
                valid_until=self.ca_manager.get_certificate_not_after(cert_obj),
                serial_number=str(self.ca_manager.get_certificate_serial_number(cert_obj)),
                auto_renew=auto_renew,
                renewal_threshold_days=renewal_threshold_days
            )

            # Update resource with certificate reference
            resource.update_record(tls_cert_id=cert_id)
            self.db.commit()

            # Create Kubernetes Secret if applicable
            if resource.k8s_namespace and self.k8s_client:
                self._create_k8s_secret(
                    resource,
                    cert_data['certificate'],
                    cert_data['private_key']
                )

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action='certificate_generated',
                resource_type='certificate',
                resource_id=cert_id,
                team_id=resource.team_id,
                details={
                    'resource_id': resource_id,
                    'ca_id': ca_id,
                    'common_name': common_name,
                    'auto_renew': auto_renew
                }
            )

            logger.info(f"Generated certificate {cert_id} for resource {resource_id}")

            return {
                'id': cert_id,
                'resource_id': resource_id,
                'ca_id': ca_id,
                'common_name': common_name,
                'san_dns': san_dns,
                'san_ips': san_ips,
                'valid_from': self.ca_manager.get_certificate_not_before(cert_obj),
                'valid_until': self.ca_manager.get_certificate_not_after(cert_obj),
                'auto_renew': auto_renew
            }

        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}")
            raise

    def list_certificates(self, resource_id: int, user_id: int) -> List[Dict[str, Any]]:
        """
        List all certificates for a resource.

        Args:
            resource_id: ID of resource
            user_id: User requesting list

        Returns:
            List of certificate dictionaries

        Raises:
            CertificateAccessDenied: If user lacks permission
            CertificateNotFound: If resource not found
        """
        resource = self.db.resources[resource_id]
        if not resource or resource.deleted_at:
            raise CertificateNotFound(f"Resource {resource_id} not found")

        self._check_certificate_view(user_id, resource.team_id)

        certs = self.db(
            (self.db.certificates.resource_id == resource_id) &
            (self.db.certificates.deleted_at == None)
        ).select()

        return [
            {
                'id': cert.id,
                'common_name': cert.common_name,
                'san_dns': cert.san_dns,
                'san_ips': cert.san_ips,
                'valid_from': cert.valid_from,
                'valid_until': cert.valid_until,
                'auto_renew': cert.auto_renew,
                'created_at': cert.created_at
            }
            for cert in certs
        ]

    def renew_certificate(self, cert_id: int, user_id: int) -> Dict[str, Any]:
        """
        Manually renew a certificate.

        Args:
            cert_id: ID of certificate to renew
            user_id: User renewing certificate

        Returns:
            Dictionary with renewed certificate details

        Raises:
            CertificateAccessDenied: If user lacks permission
            CertificateNotFound: If certificate not found
        """
        cert = self.db.certificates[cert_id]
        if not cert or cert.deleted_at:
            raise CertificateNotFound(f"Certificate {cert_id} not found")

        resource = self.db.resources[cert.resource_id]
        self._check_certificate_access(user_id, resource.team_id)

        try:
            # Generate new certificate with same parameters
            result = self.generate_certificate(
                resource_id=cert.resource_id,
                ca_id=cert.ca_id,
                common_name=cert.common_name,
                auto_renew=cert.auto_renew,
                renewal_threshold_days=cert.renewal_threshold_days,
                user_id=user_id
            )

            # Soft delete old certificate
            cert.update_record(deleted_at=datetime.now())
            self.db.commit()

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action='certificate_renewed',
                resource_type='certificate',
                resource_id=result['id'],
                team_id=resource.team_id,
                details={'previous_cert_id': cert_id}
            )

            logger.info(f"Renewed certificate {cert_id}, new ID: {result['id']}")
            return result

        except Exception as e:
            logger.error(f"Failed to renew certificate: {e}")
            raise

    def revoke_certificate(self, cert_id: int, user_id: int) -> None:
        """
        Revoke a certificate (soft delete).

        Args:
            cert_id: ID of certificate to revoke
            user_id: User revoking certificate

        Raises:
            CertificateAccessDenied: If user lacks permission
            CertificateNotFound: If certificate not found
        """
        cert = self.db.certificates[cert_id]
        if not cert or cert.deleted_at:
            raise CertificateNotFound(f"Certificate {cert_id} not found")

        resource = self.db.resources[cert.resource_id]
        self._check_certificate_access(user_id, resource.team_id)

        try:
            # Soft delete certificate
            cert.update_record(deleted_at=datetime.now())

            # Remove certificate reference from resource if it's the current one
            if resource.tls_cert_id == cert_id:
                resource.update_record(tls_cert_id=None)

            self.db.commit()

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action='certificate_revoked',
                resource_type='certificate',
                resource_id=cert_id,
                team_id=resource.team_id
            )

            logger.info(f"Revoked certificate {cert_id}")

        except Exception as e:
            logger.error(f"Failed to revoke certificate: {e}")
            raise

    # ====== Kubernetes Helper Methods ======

    def _create_k8s_secret(
        self,
        resource,
        certificate_pem: str,
        private_key_pem: str
    ) -> None:
        """
        Create a Kubernetes TLS Secret with certificate and key.

        Args:
            resource: Resource object with k8s_namespace and k8s_resource_name
            certificate_pem: PEM-encoded certificate
            private_key_pem: PEM-encoded private key
        """
        if not self.k8s_client or not resource.k8s_namespace:
            return

        secret_name = f"{resource.k8s_resource_name}-tls"

        # Base64 encode certificate and key for Kubernetes Secret
        cert_b64 = base64.b64encode(certificate_pem.encode()).decode()
        key_b64 = base64.b64encode(private_key_pem.encode()).decode()

        secret_data = {
            'tls.crt': cert_b64,
            'tls.key': key_b64
        }

        try:
            self.k8s_client.create_secret(
                namespace=resource.k8s_namespace,
                name=secret_name,
                data=secret_data,
                secret_type='kubernetes.io/tls',
                labels={
                    'app': resource.name,
                    'managed-by': 'nest'
                }
            )
            logger.info(f"Created K8s TLS secret '{secret_name}'")
        except KubernetesClientException as e:
            logger.warning(f"Failed to create K8s secret: {e}")
            # Don't fail the entire operation if K8s secret creation fails
