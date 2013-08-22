% Bible2.cls
%   Last modified: 2013-08-22 by RJH
%
% XeTeX class for layout of two-column Bibles
%
% Copyright (C) 2013 Robert Hunt
% Author: Robert Hunt <robert316@users.sourceforge.net>
% License: See gpl-3.0.txt

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{Bible}[2013/08/21 custom Bible class]
\LoadClass{book}
\RequirePackage{multicol}
\RequirePackage{lettrine} % Finds lettrine.sty


% \RequirePackage{titlesec}

% \titleformat{\section}
%   {\Large\scshape\raggedright}
%   {}{0em}
%   {}
%   [\titlerule]
%
%   \titleformat{\subsection}
%   {\large\scshape\raggedright}
%   {}{0em}
%   {}
%
%   \newcommand{\datedsection}[2]{
%   \section[#1]{#1 \hfill #2}
% }


\newcommand{\BibleBook}[1]{
  \newpage
  \centerline{\Huge{#1}}
}

\newcommand{\BibleIntro}[0]{
  \\ % Was \part but messes things up
}
\newcommand{\BibleText}[0]{
  \\ % Was \part but messes things up
  \begin{multicols}{2}
}

\newcommand{\BibleTextSection}[1]{
  \section{#1}
}

\newcommand{\BibleSectionReference}[1]{
  \centerline{#1}
  \newline
}


% Chapter and verse numbers
\newcommand{\chapterNumber}[1]{
    \lettrine[lines=3,slope=-4pt,nindent=-4pt]{#1}{~}
}
% {\em #1}

\newcommand{\verseNumber}[1]{
    \textsuperscript{#1~}
}


% Biblical text styles
\newcommand{\BibleParagraphStyleIP}[0]{
    \par
}


% Biblical text styles
\newcommand{\BibleParagraphStyleP}[0]{
    \par
}
\newcommand{\BibleParagraphStylePI}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQQQQ}[0]{
    \par
}


\newcommand{\endBibleBook}[0]{
    \end{multicols}
}

% \newcommand{\contact}[5]{
%     #1 {\large\textperiodcentered} #2 {\large\textperiodcentered} #3
%     {\Large} #4 \ {\Large} #5
% }
%
% \newcommand{\longcontact}[5]{
%     \center{#1 \hfill {\large\textperiodcentered} \hfill #2 \hfill {\large\textperiodcentered} \hfill #3}
%     \center{ {\Large} #4 \hfill {\Large} #5}
% }
%
% \newcommand{\workitems}[3]{
%     \begin{itemize}
%     \item #1
%     \item #2
%     \item #3
%     \end{itemize}
% }