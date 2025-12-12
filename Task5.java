public class Task5 {
    public static void main(String[] args) {
        // Проверка: есть ли аргументы
        if (args.length == 0) {
            System.out.println("Аргументы командной строки не переданы.");
            return;
        }

        System.out.println("Аргументы командной строки:");

        // Цикл for по индексам
        for (int i = 0; i < args.length; i++) {
            System.out.println("Аргумент " + i + ": " + args[i]);
        }
    }
}

