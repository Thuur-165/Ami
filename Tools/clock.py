"""
Ferramenta padrão de exemplo para data e hora

Escrita originalmente por Arthur (Desenvolvedor original)
"""

from .tool_registry import tool
from typing import Optional
import datetime
import pytz

class SistemaRelogio:
    """
    Sistema para obtenção de horários em diferentes fusos horários.
    
    Este sistema permite consultar o horário atual em diversos países
    ou fusos horários específicos, com formatação adequada para o Brasil.
    """
    
    def __init__(self) -> None:
        """Inicializa o sistema de relógio com mapeamento de países para fusos horários"""
        self.mapeamento_paises = {
            'brasil': 'America/Sao_Paulo',
            'brazil': 'America/Sao_Paulo',
            'portugal': 'Europe/Lisbon',
            'espanha': 'Europe/Madrid',
            'spain': 'Europe/Madrid',
            'frança': 'Europe/Paris',
            'france': 'Europe/Paris',
            'alemanha': 'Europe/Berlin',
            'germany': 'Europe/Berlin',
            'italia': 'Europe/Rome',
            'italy': 'Europe/Rome',
            'reino unido': 'Europe/London',
            'uk': 'Europe/London',
            'eua': 'America/New_York',
            'usa': 'America/New_York',
            'japao': 'Asia/Tokyo',
            'japan': 'Asia/Tokyo',
            'china': 'Asia/Shanghai',
            'australia': 'Australia/Sydney',
            'india': 'Asia/Kolkata',
            'russia': 'Europe/Moscow',
            'canada': 'America/Toronto',
            'mexico': 'America/Mexico_City',
            'argentina': 'America/Argentina/Buenos_Aires'
        }
        
        # Mapeamento dos dias da semana em inglês para português
        self.dias_semana = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }

    @tool
    def obter_horario(self, pais: Optional[str] = '') -> str:
        """
        Obtém o horário atual em formato brasileiro (DD-MM-AAAA HH:mm, Dia da semana).
        
        Use esta ferramenta quando precisar verificar o horário atual em qualquer parte do mundo.
        Se não especificar país, retorna o horário local do sistema.
        
        Args:
            pais: País ou fuso horário específico para consulta (opcional) SEM ACENTOS!
        
        Returns:
            String formatada com data, horário e dia da semana no formato:
            "Horário atual: DD-MM-AAAA às HH:mm (Dia da semana) [Fuso horário]"
            Exemplo: "Horário atual: 16-11-2025 às 14:30 (Domingo) (Brasil)"
        """
        try:
            # Se não foi especificado país, usa horário local
            if not pais or pais.strip() == '':
                now = datetime.datetime.now()
                fuso_horario_nome = 'Local'
            else:
                # Normaliza o nome do país (minúsculo e sem espaços extras)
                pais_normalizado = pais.lower().strip()
                
                # Busca o fuso horário correspondente
                if pais_normalizado in self.mapeamento_paises:
                    fuso_horario = pytz.timezone(self.mapeamento_paises[pais_normalizado])
                    now = datetime.datetime.now(fuso_horario)
                    fuso_horario_nome = pais.title()
                else:
                    # Tenta usar como fuso horário diretamente
                    try:
                        fuso_horario = pytz.timezone(pais)
                        now = datetime.datetime.now(fuso_horario)
                        fuso_horario_nome = pais
                    except pytz.exceptions.UnknownTimeZoneError:
                        # Usa horário local com aviso
                        now = datetime.datetime.now()
                        fuso_horario_nome = f'Local (país "{pais}" não reconhecido)'
            
            # Formata a data no formato brasileiro DD/MM/AAAA
            data_str = now.strftime('%d-%m-%Y')
            
            # Formata a hora HH:mm
            hora_str = now.strftime('%H:%M')
            
            # Obtém o dia da semana em inglês e converte para português
            dia_semana_en = now.strftime('%A')
            dia_semana_pt = self.dias_semana.get(dia_semana_en, dia_semana_en)
            
            # Monta a string final no formato brasileiro
            resultado = f'{data_str} às {hora_str} ({dia_semana_pt})'
            
            # Adiciona informação do fuso horário se não for local
            if fuso_horario_nome != 'Local':
                resultado += f' ({fuso_horario_nome})'
                
            return resultado
            
        except Exception as e:
            return f'Erro ao obter horário: {str(e)}. Verifique se o nome do país está correto.'