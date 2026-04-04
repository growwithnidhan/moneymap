# AWS Provider Configuration
provider "aws" {
  region = "ap-south-1"  # Mumbai region
}

# EC2 Instance for Django App
resource "aws_instance" "moneymap_server" {
  ami           = "ami-0f58b397bc5c1f2e8"
  instance_type = "t2.micro"  # Free tier

  tags = {
    Name = "moneymap-server"
  }
}

# Security Group
resource "aws_security_group" "moneymap_sg" {
  name = "moneymap-security-group"

  # Allow HTTP
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS MySQL Database
resource "aws_db_instance" "moneymap_db" {
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"  # Free tier
  username       = "admin"
  password       = "moneymap123"
  skip_final_snapshot = true

  tags = {
    Name = "moneymap-database"
  }
}