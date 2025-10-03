from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import uuid
import datetime


@dataclass
class Usuario:
    id: str
    nombre: str
    correo: str
    tipo: str  # 'estudiante_pre', 'estudiante_pos', 'docente', 'administrativo', 'externo'
    fecha_registro: datetime.date

    @staticmethod
    def nuevo(nombre: str, correo: str, tipo: str) -> 'Usuario':
        return Usuario(id=str(uuid.uuid4()), nombre=nombre, correo=correo, tipo=tipo, fecha_registro=datetime.date.today())


class IUserValidator(ABC):
    @abstractmethod
    def validar(self, usuario: Usuario) -> None:
        """Lanza ValueError si no es válido"""

class UsuarioValidator(IUserValidator):
    def validar(self, usuario: Usuario) -> None:
        if not usuario.nombre or len(usuario.nombre.strip()) < 2:
            raise ValueError("Nombre inválido")
        if '@' not in usuario.correo or len(usuario.correo.strip()) < 5:
            raise ValueError("Correo inválido")
        tipos = {'estudiante_pre', 'estudiante_pos', 'docente', 'administrativo', 'externo'}
        if usuario.tipo not in tipos:
            raise ValueError(f"Tipo de usuario desconocido: {usuario.tipo}")


class ICostoCarne(ABC):
    @abstractmethod
    def calcular(self, usuario: Usuario) -> float:
        pass

class CostoEstudiantePre(ICostoCarne):
    def calcular(self, usuario: Usuario) -> float:
        return 10.0

class CostoEstudiantePos(ICostoCarne):
    def calcular(self, usuario: Usuario) -> float:
        return 12.0

class CostoDocente(ICostoCarne):
    def calcular(self, usuario: Usuario) -> float:
        return 5.0

class CostoAdministrativo(ICostoCarne):
    def calcular(self, usuario: Usuario) -> float:
        return 6.0

class CostoExterno(ICostoCarne):
    def calcular(self, usuario: Usuario) -> float:
        return 20.0

class CostoFactory:
    _mapping = {
        'estudiante_pre': CostoEstudiantePre,
        'estudiante_pos': CostoEstudiantePos,
        'docente': CostoDocente,
        'administrativo': CostoAdministrativo,
        'externo': CostoExterno,
    }

    @classmethod
    def get_costo_strategy(cls, tipo: str) -> ICostoCarne:
        if tipo not in cls._mapping:
            raise ValueError(f"No hay estrategia de costo para tipo: {tipo}")
        return cls._mapping[tipo]()



class ICardGenerator(ABC):
    @abstractmethod
    def generar(self, usuario: Usuario, costo: float) -> bytes:
        pass

class SimpleCardGenerator(ICardGenerator):
    def generar(self, usuario: Usuario, costo: float) -> bytes:
        contenido = (
            f"CARNE BIBLIOTECA UNSCH\n"
            f"Nombre: {usuario.nombre}\n"
            f"ID: {usuario.id}\n"
            f"Tipo: {usuario.tipo}\n"
            f"Costo: S/ {costo:.2f}\n"
            f"Fecha: {usuario.fecha_registro.isoformat()}\n"
        )
        return contenido.encode('utf-8')




class INotifier(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, asunto: str, cuerpo: str, attachment: Optional[bytes] = None) -> None:
        pass

class EmailNotifier(INotifier):
    def __init__(self, smtp_server: str = 'smtp.example.com', smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def enviar(self, destinatario: str, asunto: str, cuerpo: str, attachment: Optional[bytes] = None) -> None:
        print(f"[EmailNotifier] Enviando email a {destinatario}: {asunto}\n{cuerpo[:80]}...")
        if attachment:
            print(f"[EmailNotifier] Attachment size: {len(attachment)} bytes")

# ---------------------------
# Repository
# ---------------------------
class IRepository(ABC):
    @abstractmethod
    def guardar_usuario(self, usuario: Usuario, costo: float, carne_bin: bytes) -> None:
        pass

class InMemoryRepository(IRepository):
    def __init__(self):
        self._store = []

    def guardar_usuario(self, usuario: Usuario, costo: float, carne_bin: bytes) -> None:
        self._store.append({'usuario': usuario, 'costo': costo, 'carne': carne_bin})
        print(f"[InMemoryRepository] Usuario {usuario.id} guardado (mem). Total registros: {len(self._store)}")

class MySQLRepository(IRepository):
    def __init__(self, host: str, user: str, password: str, database: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def guardar_usuario(self, usuario: Usuario, costo: float, carne_bin: bytes) -> None:
        print(f"[MySQLRepository] Guardando usuario {usuario.id} en {self.database}@{self.host}")



class IPrinter(ABC):
    @abstractmethod
    def imprimir(self, carcarn: bytes) -> None:
        pass

class ConsolePrinter(IPrinter):
    def imprimir(self, carcarn: bytes) -> None:
        print("[ConsolePrinter] Imprimiendo carné:\n")
        try:
            texto = carcarn.decode('utf-8')
            print(texto)
        except Exception:
            print(f"[ConsolePrinter] (binario) {len(carcarn)} bytes")


class GestorCarne:
    def __init__(
        self,
        validator: IUserValidator,
        repo: IRepository,
        notifier: INotifier,
        card_generator: ICardGenerator,
        printer: IPrinter,
    ):
        self.validator = validator
        self.repo = repo
        self.notifier = notifier
        self.card_generator = card_generator
        self.printer = printer

    def emitir_carne(self, usuario: Usuario) -> dict:
        self.validator.validar(usuario)
        costo_strategy = CostoFactory.get_costo_strategy(usuario.tipo)
        costo = costo_strategy.calcular(usuario)
        carne_bin = self.card_generator.generar(usuario, costo)
        self.repo.guardar_usuario(usuario, costo, carne_bin)

        asunto = "Su carné de la Biblioteca Central - UNSCH"
        cuerpo = f"Estimado/a {usuario.nombre},\nSu carné está listo.\nCosto: S/ {costo:.2f}\nID: {usuario.id}\n"
        try:
            self.notifier.enviar(usuario.correo, asunto, cuerpo, attachment=carne_bin)
        except Exception as e:
            print(f"[GestorCarne] Error enviando notificación: {e}")

        try:
            self.printer.imprimir(carne_bin)
        except Exception as e:
            print(f"[GestorCarne] Error imprimiendo carné: {e}")

        return {'usuario_id': usuario.id, 'costo': costo}


# EJEMPLO DE USO INTERACTIVO

if __name__ == '__main__':
    validator = UsuarioValidator()
    repo = InMemoryRepository()
    notifier = EmailNotifier(smtp_server='smtp.miuniversidad.edu', smtp_port=587)
    card_generator = SimpleCardGenerator()
    printer = ConsolePrinter()

    gestor = GestorCarne(validator=validator, repo=repo, notifier=notifier, card_generator=card_generator, printer=printer)

    # Pedir datos desde la terminal
    nombre = input("Ingrese el nombre completo: ")
    correo = input("Ingrese el correo: ")
    print("Tipos disponibles: estudiante_pre, estudiante_pos, docente, administrativo, externo")
    tipo = input("Ingrese el tipo de usuario: ")

    try:
        u = Usuario.nuevo(nombre, correo, tipo)
        resultado = gestor.emitir_carne(u)
        print('\n Resumen:', resultado)
    except ValueError as e:
        print(f"\n Error: {e}")